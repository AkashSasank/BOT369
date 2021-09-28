import argparse
from bot import Bot
import json
import uuid
import datetime
from misc import calc_charges

# Usage
# python simulation.py -t 3484417 -i minute -n IRCTC -m models/IRCTC_minute_epochs500 -p 0.005 -r 0.5
# python simulation.py -t 779521 -i minute -n SBIN -m models/IRCTC_minute_epochs500 -p 0.005 -r 0.5

"""
INFY 408065
SBIN 779521
IRCTC 3484417
ITC 424961
"""

parser = argparse.ArgumentParser(description='Simulation for trading.')

parser.add_argument('-t', '--instrument_token', type=int,
                    help='Instrument token of a traded instrument.')
parser.add_argument('-i', '--interval', type=str,
                    help='Interval of candlestick data.')
parser.add_argument('-n', '--name', type=str,
                    help='Instrument name.')
parser.add_argument('-m', '--model', type=str,
                    help='Default model.')
parser.add_argument('-p', '--target', type=float,
                    help='Target profit(%).', default=0.005)
parser.add_argument('-r', '--risk2reward', type=float,
                    help='Risk to reward ratio.', default=0.5)
parser.add_argument('-c', '--confidence', type=float,
                    help='Probability threshold to enter trade.', default=0.5)

parser.print_usage()

args = parser.parse_args()

instrument_token = args.instrument_token
interval = args.interval
name = args.name
model = args.model
target = args.target
risk2reward = args.risk2reward
confidence = args.confidence

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
target_profit = 0.01
target_stoploss = 0.005
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
    'target_profit_percentage': target,
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

            with open(file, mode='w') as f:
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
                json.dump(data, f)

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

with open(file, mode='w') as f:
    data['trades'] = trades
    data['profit'] = total_profit
    data['time_end'] = str(datetime.datetime.now())
    json.dump(data, f)
