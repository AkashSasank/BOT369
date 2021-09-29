import argparse
from bot import Bot
import json
import uuid
import datetime
from misc import calc_charges

from apps.ledger.tasks import save_json

# Usage
# python simulation.py -t 3484417 -i minute -n IRCTC -m models/IRCTC_minute_epochs500 -p 0.005 -r 0.5
# python simulation.py -t 779521 -i minute -n SBIN -m models/IRCTC_minute_epochs500 -p 0.005 -r 0.5

"""
INFY 408065
SBIN 779521
IRCTC 3484417
ITC 424961
"""


def simulate_trade(instrument_token, interval, name, model, target, session_target, risk2reward, confidence):
    """
    Function to simulate live trade session.
    :param instrument_token: Instrument token
    :param interval: timeframe
    :param name: Instrument name
    :param model: ML model name
    :param target: Target profit % per trade
    :param session_target: Target profit % per session
    :param risk2reward: Multiplier for calculating stoploss percentage
    :param confidence: Confidence threshold for ml model output
    :return:
    """
    # Time settings
    start_time = datetime.time(8, 15, 0)
    square_off_time = datetime.time(21, 45, 0)

    now = datetime.datetime.now().time()
    if square_off_time >= now >= start_time:
        print('Initialising BOT')
    else:
        print('Trading time is over.')
        exit()

    # Initialise BOT
    bot = Bot(instrument_token=instrument_token, interval=interval, instrument_name=name,
              default_model=model, usable_margin=1)

    # Calculate limits for the bot
    target_profit = session_target
    target_stoploss = session_target * risk2reward
    usable_margin = bot.usable_margin
    expected_profit = usable_margin * target_profit
    expected_loss = usable_margin * target_stoploss * -1

    # Initialise log data
    date = datetime.date.today()
    file = 'media/' + 'simulation_log_' + str(date) + name + str(uuid.uuid4()) + '.json'
    quantity = bot.min_tradable_qty * bot.boco_multiplier
    data = {
        'instrument_name': name,
        'instrument_token': instrument_token,
        'type': 'simulation',
        'timeframe': interval,
        'ml_model': model,
        'target_profit_percentage': session_target,
        'r2r': risk2reward,
        'time_start': str(datetime.datetime.now()),
        'max_profit': expected_profit,
        'stoploss': expected_loss,
        'quantity': quantity
    }

    # Initialise variables
    trades = {}
    total_profit = 0
    number_of_trades = 0
    profitable_trades = 0
    non_profitable_trades = 0
    charges = 0

    p = 0
    loss = 0
    tf1 = interval
    tf2 = interval

    interval = tf1

    smal = bot.support2
    smah = bot.support1
    longsma = bot.support
    change = True

    while True:
        now = datetime.datetime.now().time()
        if now >= square_off_time:
            print('Trading time is over')
            break
        try:
            profit = 0
            trade = bot.simulate_trade(risk_multiplier=risk2reward, target_profit=target, strategy='ramp',
                                       confidence=confidence, exit_on_low_confidence=True, interval=interval,
                                       square_off_time=square_off_time, smal=smal, smah=smah, longsma=longsma)
            print('Trades: ', trades)

            if trade:
                print(trade)
                # Default support levels
                smal = bot.support2
                smah = bot.support1
                longsma = bot.support
                profit_per_share = trade['pl']
                if trade['type'] == 'Buy':
                    # Calculate price per share after applying leverage
                    bp = trade['entry'] / bot.boco_multiplier
                    sp = bp + profit_per_share
                    resp = calc_charges(bp=bp, sp=sp, qty=quantity, exchange=bot.exchange)
                if trade['type'] == 'Sell':
                    # Calculate price per share after applying leverage
                    sp = trade['entry'] / bot.boco_multiplier
                    bp = sp - profit_per_share
                    resp = calc_charges(bp=bp, sp=sp, qty=quantity, exchange=bot.exchange)
                trade['charges'] = resp
                trade['quantity'] = quantity
                trades[str(datetime.datetime.now())] = trade
                number_of_trades = number_of_trades + 1
                # pl = trade['pl']
                pl = resp['net_profit']
                charges = charges + resp['total_charges']
                profit = profit + pl
                total_profit = total_profit + profit
                if pl > 0:
                    p = p + pl
                    profitable_trades = profitable_trades + 1
                    interval = tf1
                    #     Adjust stoploss
                    # expected_profit = expected_profit + pl
                    expected_loss = expected_loss + pl
                    data['stoploss'] = expected_loss

                else:
                    loss = loss + pl
                    non_profitable_trades = non_profitable_trades + 1
                    # Trade at lower TF in case of loss
                    interval = tf2

                # TODO ASYNC task to save the json file
                data['trades'] = trades
                data['number_of_trades'] = number_of_trades
                data['profitable_trades'] = profitable_trades
                data['non_profitable_trades'] = non_profitable_trades
                data['p+'] = p
                data['p-'] = loss
                data['charges'] = charges
                data['gross_profit'] = total_profit + charges
                data['net_profit'] = total_profit
                data['time_end'] = str(datetime.datetime.now())
                save_json.apply_async(queue='default', args=(file, data))

                # Stop bot once target profit is reached
                if total_profit >= expected_profit or total_profit <= expected_loss:
                    print('Stopping BOT.')
                    break
            else:
                # Alter the support levels (SMA) to check if there is an entry
                if change:
                    smal = bot.support3
                    smah = bot.support2
                    longsma = bot.support1
                    change = not change
                else:
                    smal = bot.support2
                    smah = bot.support1
                    longsma = bot.support
                    change = not change

            print('Profit: ', profit)
            print('Total profit: ', total_profit)

        except Exception as e:
            print(e)
            # Retry after 10 seconds
            import time

            time.sleep(10)
        except KeyboardInterrupt:
            print('Exiting BOT manually.')
            break

    data['trades'] = trades
    data['profit'] = total_profit
    data['time_end'] = str(datetime.datetime.now())
    save_json.apply_async(queue='default', args=(file, data))
