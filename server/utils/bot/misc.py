from bs4 import BeautifulSoup
import requests


def calc_charges(instrument_type='intraday', bp=0, sp=0, qty=0, exchange='NSE'):
    """
    Calculate charges for a trade. The calculations are based on methods listed
    in official page of zerodha as on 07-04-2021.
    :param instrument_type: Type of instrument => intraday, delivery
    :param bp: float: buy price
    :param sp: float: sell price
    :param qty:int : quantity
    :param exchange: stock exchange => NSE, BSE
    :return: dict() => {
            'brokerage': brokerage,
            'turnover': turnover,
            'STT': stt_total,
            'GST': stax,
            'sebi_charges': sebi_charges,
            'stamp_duty': stamp_charges,
            'total_charges': total_tax,
            'breakeven': breakeven,
            'net_profit': net_profit
        }
    """
    assert bp > 0
    assert sp > 0
    assert qty > 0
    assert exchange in ['NSE', 'BSE']
    # TODO : Add calculations for other instrument types
    assert instrument_type in ['intraday', 'delivery']

    if instrument_type == 'intraday':

        brokerage_buy = 20 if (bp * qty * 0.0003) > 20 else round((bp * qty * 0.0003), 2)
        brokerage_sell = 20 if (sp * qty * 0.0003) > 20 else round((sp * qty * 0.0003), 2)
        brokerage = round(brokerage_sell + brokerage_buy, 2)

        turnover = round((bp + sp) * qty, 2)
        stt_total = round(((sp * qty) * 0.00025), 2)
        if exchange == 'NSE':
            exc_trans_charge = round((0.0000345 * turnover), 2)
        if exchange == 'BSE':
            exc_trans_charge = round((0.0000345 * turnover), 2)
        cc = 0
        stax = round((0.18 * (brokerage + exc_trans_charge)), 2)
        sebi_charges = round((turnover * 0.0000005), 2)
        stamp_charges = round(((bp * qty) * 0.00003), 2)
        total_tax = round((brokerage + stt_total + exc_trans_charge + cc + stax + sebi_charges + stamp_charges), 2)
        breakeven = round(total_tax / qty, 2)
        net_profit = round((((sp - bp) * qty) - total_tax), 2)

        return {
            'brokerage': brokerage,
            'turnover': turnover,
            'STT': stt_total,
            'GST': stax,
            'sebi_charges': sebi_charges,
            'stamp_duty': stamp_charges,
            'total_charges': total_tax,
            'breakeven': breakeven,
            'net_profit': net_profit
        }


def get_intraday_margins(instrument_name):
    """
    Find the margin and multipler for a given instrument.
    :param instrument_name: Listed name of the instrument
    :return: dict() => {'mis_margin': mis_margin,
     'mis_multiplier': mis_multiplier,
     'boco_margin': boco_margin,
     'boco_multiplier': boco_multiplier}
    """
    try:
        url = "https://zerodha.com/margin-calculator/Equity/"
        req = requests.get(url)
        soup = BeautifulSoup(req.content, 'html.parser')
        instrument = soup.find(attrs={'data-scrip': instrument_name})
        mis_margin = instrument.find('td', attrs={'class': 'mis_margin'}).text
        mis_multiplier = instrument.find('td', attrs={'class': 'mis_multiplier'}).text
        boco_margin = instrument.find('td', attrs={'class': 'boco_margin'}).text
        boco_multiplier = instrument.find('td', attrs={'class': 'boco_multiplier'}).text
        return {
            'mis_margin': float(mis_margin.split('\n')[1].split('\t')[-1].split('%')[0]),
            'mis_multiplier': float(mis_multiplier.split('\n')[1].split('\t')[-1].split('x')[0]),
            'boco_margin': float(boco_margin.split('\n')[1].split('\t')[-1].split('%')[0]),
            'boco_multiplier': float(boco_multiplier.split('\n')[1].split('\t')[-1].split('x')[0])

        }
    except Exception as e:
        print('Invalid instrument: {}'.format(instrument_name))