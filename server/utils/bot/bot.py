import os
from kite_wrapper import Kite, TechnicalAnalysisV2, TechnicalAnalysis
import pandas as pd
import autokeras as ak
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.layers import Input, Dense, BatchNormalization, Dropout
from tensorflow.keras.utils import to_categorical
import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix
import seaborn as sn
import matplotlib.pyplot as plt
import shutil
import datetime
import time
from misc import get_intraday_margins


class Envs:
    """
    Class to initialise environment variables.
    """
    def __init__(self):
        self._API_KEY = os.getenv('API_KEY')
        self._API_SECRET = os.getenv('API_SECRET')
        self._REDIRECT_URL = os.getenv('REDIRECT_URL')
        self._USER_ID = os.getenv('USER_ID')
        self._PASSWORD = os.getenv('PASSWORD')
        self._PIN = os.getenv('PIN')


class Bot(Envs):
    """
    Class to initialise trading bot and perform different actions like simulation, model training, live trade etc.
    """
    def __init__(self, instrument_token, default_model=None, instrument_name: str = 'stock', interval='minute',
                 usable_margin: float = 0.2,
                 segment='equity', exchange='NSE',
                 instrument_type='intraday',
                 use_leverage=True):
        super().__init__()
        self.instrument_token = instrument_token
        self.instrument_name = instrument_name
        self.interval = interval
        assert 0 < usable_margin <= 1
        assert segment in ['equity', 'commodity', 'currency']
        assert instrument_type in ['delivery', 'intraday', 'futures', 'options']
        assert exchange in ['NSE', 'BSE']
        self.exchange = exchange
        self.instrument_type = instrument_type
        self.segment = segment
        self.use_leverage = use_leverage
        if default_model:
            self.model_name = default_model
            self.model = self.load_model(self.model_name)
        self.kite = Kite(self._API_KEY, self._API_SECRET, self._REDIRECT_URL)
        self.trading_symbol = self.kite.get_trading_symbol(self.instrument_token)

        if not self.kite.validate_token():
            if self._USER_ID and self._PASSWORD and self._PIN:
                self.kite.connect(auto=True, user_id=self._USER_ID, password=self._PASSWORD, pin=self._PIN)
            else:
                self.kite.connect()
        self.margins = self.kite.session.margins(segment=self.segment)
        self.net_margin = self.margins['net']
        self.usable_margin = usable_margin * self.net_margin
        ltp = self.kite.session.ltp(self.instrument_token)[str(self.instrument_token)][
            'last_price']
        try:
            assert self.usable_margin > ltp
        except AssertionError:
            print("""
                       Insufficient margin. Add fund or increase usable margin.
                   """)
            return
        self.min_tradable_qty = self.usable_margin // ltp
        self.data = self.kite.get_historic_data(self.instrument_token, self.interval, sets=1)
        self.analysis = TechnicalAnalysisV2(self.data, self.instrument_name)
        self.support = self.analysis.get_best_moving_average(max_length=500)
        self.support1 = self.support // 3
        self.support2 = self.support // 9
        self.support3 = self.support // 18
        # self.analysis.plot_chart(moving_averages=(self.support, self.support1, self.support2), length=500)
        # time.sleep(2)
        self.tick_size = 0.05
        margins = get_intraday_margins(self.trading_symbol)
        self.mis_margin = margins['mis_margin']
        self.mis_multiplier = margins['mis_multiplier']
        self.boco_margin = margins['boco_margin']
        self.boco_multiplier = margins['boco_multiplier']

    def train(self, max_trials=10, epochs=10, interval=None, ramp=False, swing=False, sets=1):
        """
        Train ML model to predict  trade action. Auto ML is used to train multiple models on a
         dataset and choose the best model.
        :param max_trials: int :
        :param epochs:
        :param interval:
        :param ramp:
        :param swing:
        :param sets:
        :return:
        """
        if not interval:
            interval = self.interval
        data = self.kite.get_historic_data(self.instrument_token, interval, sets=sets)
        analysis = TechnicalAnalysisV2(data, self.instrument_name)
        analysis.generate_data_set(ramp=ramp, swing=swing)
        filename = self.instrument_name + '.csv'
        x_train, y_train = self.load_dataset(filename)
        num_classes = len(list(y_train.unique()))
        clf = ak.StructuredDataClassifier(
                overwrite=True,
                max_trials=max_trials,
                project_name='models/' + self.instrument_name + '_ml_trading_bot_' + interval, num_classes=num_classes)
        # Feed the structured data classifier with training data.
        clf.fit(x_train, y_train, epochs=epochs)
        # Evaluate the best model with testing data.
        print(clf.evaluate(x_train, y_train))
        model = clf.export_model()
        model.summary()
        model_name = 'models/' + self.instrument_name + '_' + interval + '_epochs' + str(epochs)
        try:
            model.save(model_name, save_format="tf")
        except Exception as e:
            model.save(model_name + '.h5')
        print("""
                Trained ML model successfully.
        """)

    def train_model(self, epochs=10000, interval=None, ramp=False, swing=False, sets=1):
        if not interval:
            interval = self.interval
        # data = self.kite.get_historic_data(self.instrument_token, interval, sets=sets)
        # analysis = TechnicalAnalysisV2(data, self.instrument_name)
        # analysis.generate_data_set(ramp=ramp, swing=swing)
        filename = self.instrument_name + '.csv'
        x_train, y_train = self.load_dataset(filename, categorical=True, labels=['Buy', 'Sell'])
        input_shape = x_train.shape[1]
        # output_shape = y_train.shape[1]
        print(x_train)
        print(y_train)
        model_name = 'models/' + self.instrument_name + '_' + interval + '_epochs' + str(epochs)
        opt = tf.keras.optimizers.Adam(learning_rate=0.005)
        log_dir = 'logs/' + model_name
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)
        tb = tf.keras.callbacks.TensorBoard(log_dir=log_dir)
        x_in = Input(input_shape)
        x = Dense(32, activation='relu')(x_in)
        x = Dense(32, activation='relu')(x)
        x = Dense(32, activation='relu')(x)
        # x = Dropout(0.1)(x)
        # x = Dense(1024, activation='relu')(x)
        x_out = Dense(1, activation='sigmoid')(x)

        model = Model(inputs=x_in, outputs=x_out)
        model.compile(optimizer=opt, metrics=['accuracy'], loss='mse', )
        model.summary()
        history = model.fit(x_train, y_train, batch_size=x_train.shape[0] // 10, epochs=epochs, validation_split=0.3,
                            callbacks=[tb])
        try:
            model.save(model_name, save_format="tf")
        except Exception as e:
            model.save(model_name + '.h5')
        print("""
                       Trained ML model successfully.
               """)

    @staticmethod
    def load_dataset(filename, labels: list = [], categorical=False):
        x_train = pd.read_csv(filename)
        y_train = x_train.pop('actions')
        if categorical:
            num_classes = len(labels)
            assert num_classes >= 2
            y = [labels.index(i) for i in y_train]
            y_train = to_categorical(y, num_classes)

        return x_train.to_numpy(), np.array(y_train)

    def analyse_model(self, model_name, x, y, plot_confusion_matrix=False, labels: list = []):
        model = self.load_model(model_name)
        prediction = model.predict(tf.expand_dims(x, -1))
        y_pred = np.argmax(prediction, axis=1)
        y_true = [labels.index(i) for i in y]
        cmat = confusion_matrix(y_true, y_pred)
        if plot_confusion_matrix:
            sn.heatmap(cmat, annot=True)
            plt.show()
        return cmat

    @staticmethod
    def load_model(model_name):
        loaded_model = load_model(model_name, custom_objects=ak.CUSTOM_OBJECTS)
        return loaded_model

    def predict_action(self, model_name=None, strategy='swing', interval=None, smal=20, smah=40, longsma=100):
        """
        :param model_name:
        :param strategy:
        :param interval:
        :param smal:
        :param smah:
        :param longsma:
        :return:
        """
        if model_name:
            loaded_model = self.load_model(model_name)
        else:
            loaded_model = self.model

        if not interval:
            interval = self.interval
        response = self.kite.get_trend_and_input_features('rsi_6', 'rsi_10', 'pdi', 'mdi', 'adx', 'kdjk',
                                                          'kdjd', 'kdjj', 'wr_6', 'wr_10', 'vwap',
                                                          instrument_token=self.instrument_token,
                                                          interval=interval, smah=smah,
                                                          smal=smal, longsma=longsma)
        indicators = response['indicator_values']

        if strategy == 'swing':
            labels = ['Buy', 'Hold', 'Sell']
        if strategy == 'swing2':
            labels = ['Buy', 'Hold-Up', 'Hold-Down', 'Sell']
        if strategy == 'ramp':
            labels = ['Buy', 'Sell']
        num_classes = len(labels)
        inputs = list(indicators.values())
        inputs = tf.expand_dims(inputs, 0)
        prediction = loaded_model.predict(tf.expand_dims(inputs, -1))[0]

        if num_classes == 2:
            # Handle single output node case
            p = [[i, 1 - i] for i in prediction]
            prediction = p[0]
        index = np.argmax(prediction)

        data = dict()
        data['trading_symbol'] = self.trading_symbol
        data['action'] = labels[index]
        data['probability'] = prediction[index]
        action = {}
        for index, label in enumerate(labels):
            action[label] = prediction[index]
        data['actions'] = action
        return data, response

    def simulate_trade(self, model_name=None, confidence=0.55, target_profit=0.005, risk_multiplier=0.5,
                       exit_on_low_confidence=False, exit_on_trend_reversal=True, follow_trend=True, strategy='swing',
                       interval=None, square_off_time=datetime.datetime.now().time(), auto_stoploss=True,
                       smal=None, smah=None, longsma=None, exit_on_no_trend=True):
        """
        perform trade based on predicted actions
        :param model_name:
        :param confidence:
        :param target_profit:
        :param risk_multiplier:
        :param exit_on_low_confidence:
        :param exit_on_trend_reversal:
        :param exit_on_no_trend: Boolean. Exit trade if there is no trend.
        :param follow_trend:
        :param strategy: Strategy to use for trading
                swing : Checks for swing highs, swing lows or anything in between. Give actions Buy, Hold or Sell.
                swing2 : Checks for swing highs, swing lows, up or down movements. Give actions Buy, Hold-Up, Hold-Down
                 or Sell.
                ramp : Checks for up or down movements. Give actions Buy or Sell.
        :param square_off_time:
        :param interval:
        :param auto_stoploss: automatically calculate stoploss from support values
        :param smah:
        :param smal:
        :param longsma:
        :return:
        """
        now = datetime.datetime.now().time()

        if now > square_off_time:
            print('Trading time over.')
            exit()
        if not interval:
            interval = self.interval
        if not smal:
            smal = self.support2
        if not smah:
            smah = self.support1
        if not longsma:
            longsma = self.support

        # TODO: Handle timeout
        actions, response = self.predict_action(model_name=model_name, strategy=strategy, interval=interval,
                                                smal=smal, smah=smah, longsma=longsma)
        initial_trend = response['trend']
        ltp = response['ltp']
        initial_action = actions['action']
        probability = actions['probability']
        trade_type = None
        trade = dict()
        pull_back = False
        print(actions)
        print(initial_trend)
        if probability <= confidence:
            print('Better not enter the trade on low confidence.')
            return
        if initial_trend == 'None':
            print('Better not enter the trade on no trend.')
            return

        """
        Identify trade type for each strategy
        """
        if strategy == 'swing':
            """
            Checks for swing highs, swing lows or anything in between. Give actions Buy, Hold or Sell.
            """
            if initial_trend == 'Long':
                if initial_action == 'Buy':
                    trade_type = 'Buy'
                    print('Long entry')
                    trade['entry_type'] = 'Long entry'
                elif initial_action == 'Hold':
                    predictions = actions['actions']
                    if predictions['Buy'] >= predictions['Sell']:
                        trade_type = 'Buy'
                        print('Long entry')
                        trade['entry_type'] = 'Long entry'
                    if not follow_trend:
                        if predictions['Buy'] < predictions['Sell']:
                            trade_type = 'Sell'
                            print('Pull back in Long entry')
                            trade['entry_type'] = 'Pull back in Long entry'
                            pull_back = True
                        else:
                            print('Better not enter the trade against trend.')
                            return

                # risky
                else:
                    if not follow_trend:
                        trade_type = 'Sell'
                        print('Pull back in Long entry')
                        trade['entry_type'] = 'Pull back in Long entry'
                        pull_back = True
                    else:
                        print('Better not enter the trade against trend.')
                        return

            elif initial_trend == 'Short':
                if initial_action == 'Sell':
                    trade_type = 'Sell'
                    print('Short entry')
                    trade['entry_type'] = 'Short entry'
                elif initial_action == 'Hold':
                    predictions = actions['actions']
                    if predictions['Buy'] <= predictions['Sell']:
                        trade_type = 'Sell'
                        print('Short entry')
                        trade['entry_type'] = 'Short entry'
                    if not follow_trend:
                        if predictions['Buy'] > predictions['Sell']:
                            trade_type = 'Buy'
                            print('Pull back in Short entry')
                            trade['entry_type'] = 'Pull back in Short entry'
                            pull_back = True
                        else:
                            print('Better not enter the trade against trend.')
                            return
                #         risky
                else:
                    if not follow_trend:
                        trade_type = 'Buy'
                        print('Pull back in Short entry')
                        trade['entry_type'] = 'Pull back in Short entry'
                        pull_back = True
                    else:
                        print('Better not enter the trade against trend.')
                        return

        elif strategy == 'ramp':
            print(strategy)
            """
            Checks for up or down movements. Give actions Buy or Sell.
            """
            if initial_trend == 'Long':
                if initial_action == 'Buy':
                    trade_type = 'Buy'
                    print('Long entry')
                    trade['entry_type'] = 'Long entry'
                elif initial_action == 'Sell':
                    if not follow_trend:
                        trade_type = 'Sell'
                        print('Pull back in Long entry')
                        trade['entry_type'] = 'Pull back in Long entry'
                        pull_back = True
                    else:
                        print('Better not enter the trade against trend.')
                        return

            elif initial_trend == 'Short':
                if initial_action == 'Sell':
                    trade_type = 'Sell'
                    print('Short entry')
                    trade['entry_type'] = 'Short entry'
                elif initial_action == 'Buy':
                    if not follow_trend:
                        trade_type = 'Buy'
                        print('Pull back in Short entry')
                        trade['entry_type'] = 'Pull back in Short entry'
                        pull_back = True
                    else:
                        print('Better not enter the trade against trend.')
                        return

        #     TODO: Strategy swing 2
        """
              Calculating stoploss.
              """
        stop_loss = target_profit * risk_multiplier

        """
               Calculate target and stoploss
               """
        # Target and stoploss as absolute price difference
        if pull_back:
            target = round(ltp * target_profit * 0.5, 1)
            stop_loss_target = round(ltp * stop_loss * 0.5, 1)
        else:
            target = round(ltp * target_profit, 1)
            stop_loss_target = round(ltp * stop_loss, 1)

        target = target + self.tick_size
        stop_loss_target = stop_loss_target + self.tick_size

        # Target and stop loss as actual price
        if trade_type == 'Buy':
            t_ = ltp + target
            s_ = ltp - stop_loss_target
            # Readjust stop loss to support
            if auto_stoploss:
                s1 = response['smal']
                if s_ > s1:
                    s_ = s1 - 2 * self.tick_size
                    stop_loss_target = ltp - s_
        if trade_type == 'Sell':
            t_ = ltp - target
            s_ = ltp + stop_loss_target
            # Readjust stop loss to resistance
            if auto_stoploss:
                s1 = response['smal']
                if s_ < s1:
                    s_ = s1 + 2 * self.tick_size
                    stop_loss_target = s_ - ltp
        t_ = round(t_, 1) + self.tick_size
        s_ = round(s_, 1) + self.tick_size

        print('r2r: ', '1:', target / stop_loss_target)
        trade['r2r'] = target / stop_loss_target

        if trade_type:
            """
            Initialise trade.
            """
            trade['type'] = trade_type
            entry = ltp
            trade['entry'] = entry
            trade['target'] = t_
            trade['stoploss'] = s_
            start = True
            print('Starting trade')
            print('Entry : {}'.format(ltp))
            print('Type : {}'.format(trade_type))
            running_profit = 0
            previous_running_profit = 0
            trailing_stoploss = -0.1 * stop_loss_target
            minimum_profit = self.tick_size * 5

            while start:
                # Exit on square off time
                now = datetime.datetime.now().time()
                if now >= square_off_time:
                    trade['exit'] = ltp
                    trade['pl'] = running_profit
                    start = False
                    trade['reason'] = 'Square off time.'
                    print('Reason for exit: Square off time.')
                    return trade
                actions, response = self.predict_action(model_name=model_name, strategy=strategy, interval=interval,
                                                        smal=smal, smah=smah, longsma=longsma)
                trend = response['trend']
                ltp = response['ltp']
                action = actions['action']
                probability = actions['probability']
                print('LTP : ', ltp)
                # Adjust stoploss automatically
                s1 = response['smal']
                if auto_stoploss:
                    if trade_type == 'Buy':
                        if s_ > s1:
                            s_ = s1 - 2 * self.tick_size
                            stop_loss_target = entry - s_
                    if trade_type == 'Sell':
                        if s_ < s1:
                            s_ = s1 + 2 * self.tick_size
                            stop_loss_target = s_ - entry
                    s_ = round(s_, 1) + self.tick_size
                    trade['stoploss'] = s_

                if trade_type == 'Buy':
                    running_profit = ltp - entry
                elif trade_type == 'Sell':
                    running_profit = entry - ltp
                print('Running profit :', running_profit)
                print('Target : ', t_)
                print('Stop Loss : ', s_)

                # Exit trade if running profit is less than or equal to trailing stoploss or a positive profit
                if trailing_stoploss >= running_profit >= minimum_profit:
                    print('Exit trade')
                    trade['exit'] = ltp
                    trade['pl'] = running_profit
                    trade['reason'] = 'Trailing Stoploss hit.'
                    print('Exiting trade : Trailing Stoploss hit.')

                    return trade

                # Readjust trailing stoploss
                if running_profit > minimum_profit and running_profit > previous_running_profit:
                    # trailing_stoploss = running_profit - 0.05 * stop_loss_target
                    trailing_stoploss = running_profit - minimum_profit
                    previous_running_profit = running_profit

                if exit_on_low_confidence:
                    if probability < confidence and action == initial_action:
                        # Check if loss
                        if running_profit < minimum_profit:
                            trade['exit'] = ltp
                            trade['pl'] = running_profit
                            start = False
                            trade['reason'] = 'Low confidence'
                            print('Reason for exit: Low confidence')
                            return trade

                if exit_on_trend_reversal:
                    if trend != initial_trend:
                        # Check if profit
                        if running_profit > minimum_profit:
                            trade['exit'] = ltp
                            trade['pl'] = running_profit
                            start = False
                            trade['reason'] = 'Trend reversal'
                            print('Reason for exit: Trend reversal')
                            return trade

                if trend == 'None':
                    if exit_on_no_trend:
                        trade['exit'] = ltp
                        trade['pl'] = running_profit
                        start = False
                        trade['reason'] = 'No trend.'
                        print('Reason for exit: No trend.')
                        return trade

                if trade_type == 'Buy':
                    if ltp >= t_:
                        trade['exit'] = t_
                        trade['pl'] = t_ - trade['entry']
                        start = False
                        trade['reason'] = 'Target hit'
                        print('Reason for exit: Target hit.')
                        return trade
                    elif ltp <= s_:
                        trade['exit'] = s_
                        trade['pl'] = s_ - trade['entry']
                        start = False
                        trade['reason'] = 'Stop Loss hit'
                        print('Reason for exit: Stop Loss hit.')
                        return trade

                elif trade_type == 'Sell':
                    if ltp <= t_:
                        trade['exit'] = t_
                        trade['pl'] = trade['entry'] - t_
                        start = False
                        trade['reason'] = 'Target hit'
                        print('Reason for exit: Target hit.')
                        return trade
                    elif ltp >= s_:
                        trade['exit'] = s_
                        trade['pl'] = trade['entry'] - s_
                        start = False
                        trade['reason'] = 'Stop Loss hit'
                        print('Reason for exit: Stop Loss hit.')
                        return trade

            return trade

    def trade(self, model_name=None, confidence=0.55, target_profit=0.005, risk_multiplier=0.5,
              exit_on_low_confidence=False, exit_on_trend_reversal=True, follow_trend=True,
              strategy='ramp', interval=None, order_variety='co', square_off_time=datetime.datetime.now().time(),
              auto_stoploss=True, smal=None, smah=None, longsma=None, exit_on_no_trend=True):
        """
               perform trade based on predicted actions
               :param model_name:
               :param confidence:
               :param target_profit:
               :param risk_multiplier:
               :param exit_on_low_confidence:
               :param exit_on_trend_reversal:
               :param exit_on_no_trend: Boolean. Exit trade if there is no trend.
               :param follow_trend:
               :param interval:
               :param order_variety:
               :param strategy: Strategy to use for trading
                       swing : Checks for swing highs, swing lows or anything in between. Give actions Buy, Hold or Sell.
                       swing2 : Checks for swing highs, swing lows, up or down movements. Give actions Buy, Hold-Up, Hold-Down
                        or Sell.
                       ramp : Checks for up or down movements. Give actions Buy or Sell.
                :param square_off_time:
                :param auto_stoploss:
                :param smah:
                :param smal:
                :param longsma:
               :return:
               """

        now = datetime.datetime.now().time()

        if now > square_off_time:
            print('Trading time over.')
            exit()

        if not interval:
            interval = self.interval
        if not interval:
            interval = self.interval
        if not smal:
            smal = self.support2
        if not smah:
            smah = self.support1
        if not longsma:
            longsma = self.support

        actions, response = self.predict_action(model_name=model_name, strategy=strategy, interval=interval,
                                                smal=smal, smah=smah, longsma=longsma)
        initial_trend = response['trend']
        ltp = response['ltp']
        initial_action = actions['action']
        probability = actions['probability']
        trade_type = None
        trade = dict()
        pull_back = False
        if probability <= confidence:
            print('Not entering trade due to low confidence.')
            return
        if initial_trend == 'None':
            print('Not entering trade due to no trend.')
            return

        """
        Identify trade type for each strategy
        """

        if strategy == 'ramp':
            """
            Checks for up or down movements. Give actions Buy or Sell.
            """
            if initial_trend == 'Long':
                if initial_action == 'Buy':
                    trade_type = 'BUY'
                    trade['entry_type'] = 'Long entry'
                elif initial_action == 'Sell':
                    if not follow_trend:
                        trade_type = 'SELL'
                        trade['entry_type'] = 'Pull back in Long entry'
                        pull_back = True
                    else:
                        print('Not entering trade against trend.')
                        return

            elif initial_trend == 'Short':
                if initial_action == 'Sell':
                    trade_type = 'SELL'
                    trade['entry_type'] = 'Short entry'
                elif initial_action == 'Buy':
                    if not follow_trend:
                        trade_type = 'BUY'
                        trade['entry_type'] = 'Pull back in Short entry'
                        pull_back = True
                    else:
                        print('Not entering trade against trend.')
                        return

        """
        Calculating stoploss.
        """
        stop_loss = target_profit * risk_multiplier

        """
        Calculate target and stoploss
        """
        # Target and stoploss as absolute price difference
        if pull_back:
            target = round(ltp * target_profit * 0.5, 1)
            stop_loss_target = round(ltp * stop_loss * 0.5, 1)
        else:
            target = round(ltp * target_profit, 1)
            stop_loss_target = round(ltp * stop_loss, 1)

        target = target + self.tick_size
        stop_loss_target = stop_loss_target + self.tick_size

        # Target and stop loss as actual price
        if trade_type == 'Buy':
            t_ = ltp + target
            s_ = ltp - stop_loss_target
            # Readjust stop loss to support
            if auto_stoploss:
                s1 = response['smal']
                if s_ > s1:
                    s_ = s1 - 2 * self.tick_size
                    stop_loss_target = ltp - s_
        if trade_type == 'Sell':
            t_ = ltp - target
            s_ = ltp + stop_loss_target
            # Readjust stop loss to resistance
            if auto_stoploss:
                s1 = response['smal']
                if s_ < s1:
                    s_ = s1 + 2 * self.tick_size
                    stop_loss_target = s_ - ltp
        t_ = round(t_, 1) + self.tick_size
        s_ = round(s_, 1) + self.tick_size

        if trade_type:
            """
            Initialise trade.
            """
            trade['type'] = trade_type
            entry = ltp
            trade['entry'] = entry
            trade['target'] = t_
            trade['stoploss'] = s_

            if order_variety == 'co':
                order_id = self.place_co_order(transaction_type=trade_type, trigger=ltp,
                                               stoploss=stop_loss_target)
                # FETCH CONNECTED ORDER ID
                connected_orders = \
                    list(filter(lambda d: d['parent_order_id'] in [order_id], self.kite.session.orders()))[0]
                connected_order_id = connected_orders.get('order_id')
                data = self.kite.session.order_history(order_id)
                df = data[-1]
                # Cancel order if not placed within next N seconds
                import time
                count = 0
                while 'COMPLETE' not in df.get('status'):
                    data = self.kite.session.order_history(order_id)
                    df = data[-1]
                    time.sleep(1)
                    count = count + 1
                    if count >= 5:
                        try:
                            # Cancelling current order.
                            self.kite.session.cancel_order(variety=self.kite.session.VARIETY_CO,
                                                           order_id=order_id)
                            print('Timeout')
                            print('Order cancelled.')
                            return
                        except Exception as e:
                            pass

                print('Entered trade')
                print('CO placed')

            trade['order_id'] = order_id
            running_profit = 0
            previous_running_profit = 0
            trailing_stoploss = -0.5 * stop_loss_target

            minimum_profit = self.tick_size * 5

            while True:
                # Exit on square off time
                now = datetime.datetime.now().time()
                if now >= square_off_time:
                    try:
                        self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                     order_id=connected_order_id)
                        print('Exit trade')
                        trade['exit'] = ltp
                        trade['pl'] = running_profit
                        trade['reason'] = 'Square off time.'
                        print('Exiting trade : Square off time.')
                    except Exception as e:
                        pass
                    return trade

                print('Trailing stoploss: ', trailing_stoploss)
                print('Running profit: ', running_profit)

                # Check if SL hit
                data = self.kite.session.order_history(connected_order_id)[-1]
                if 'COMPLETE' in data.get('status'):
                    trade['exit'] = s_
                    if trade_type == 'BUY':
                        pl = s_ - trade['entry']
                    if trade_type == 'SELL':
                        pl = trade['entry'] - s_
                    trade['pl'] = pl
                    trade['reason'] = 'Stop Loss hit'
                    return trade

                actions, response = self.predict_action(model_name=model_name, strategy=strategy, interval=interval,
                                                        smal=smal, smah=smah, longsma=longsma)
                trend = response['trend']
                ltp = response['ltp']
                action = actions['action']
                probability = actions['probability']
                # Adjust stoploss automatically
                s1 = response['smal']
                if auto_stoploss:
                    if trade_type == 'Buy':
                        if s_ > s1:
                            s_ = s1 - 2 * self.tick_size
                            stop_loss_target = entry - s_
                    if trade_type == 'Sell':
                        if s_ < s1:
                            s_ = s1 + 2 * self.tick_size
                            stop_loss_target = s_ - entry
                    s_ = round(s_, 1) + self.tick_size
                    trade['stoploss'] = s_
                # Calculate running profit
                if trade_type == 'BUY':
                    running_profit = ltp - entry
                if trade_type == 'SELL':
                    running_profit = entry - ltp

                # Exit trade if running profit is less than or equal to trailing stoploss or a positive profit
                if trailing_stoploss >= running_profit >= minimum_profit:
                    try:
                        self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                     order_id=connected_order_id)
                        print('Exit trade')
                        trade['exit'] = ltp
                        trade['pl'] = running_profit
                        trade['reason'] = 'Trailing Stoploss hit.'
                        print('Exiting trade : Trailing Stoploss hit.')
                    except Exception as e:
                        pass
                    return trade

                # Readjust trailing stoploss
                if running_profit > minimum_profit and running_profit > previous_running_profit:
                    # trailing_stoploss = running_profit - 0.1 * stop_loss_target
                    trailing_stoploss = running_profit - minimum_profit
                    previous_running_profit = running_profit

                if exit_on_low_confidence:
                    if probability < confidence and action == initial_action:
                        # Check if loss
                        if running_profit < minimum_profit:
                            try:
                                self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                             order_id=connected_order_id)
                                print('Exit trade')
                                trade['exit'] = ltp
                                trade['pl'] = running_profit
                                trade['reason'] = 'Low confidence'
                                print('Exiting trade : Low confidence.')

                            except Exception as e:
                                pass

                            return trade

                if exit_on_trend_reversal:
                    if trend != initial_trend:
                        # Check if profit
                        if running_profit > minimum_profit:
                            try:
                                self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                             order_id=connected_order_id)
                                print('Exit trade')
                                trade['exit'] = ltp
                                trade['pl'] = running_profit
                                trade['reason'] = 'Trend reversal'
                                print('Exiting trade : Trend reversal.')

                            except Exception as e:
                                pass
                            return trade

                if trend == 'None':
                    if exit_on_no_trend:
                        try:
                            self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                         order_id=connected_order_id)
                            print('Exit trade')
                            trade['exit'] = ltp
                            trade['pl'] = running_profit
                            trade['reason'] = 'No trend.'
                            print('Reason for exit: No trend.')

                        except Exception as e:
                            pass
                        return trade

                if trade_type == 'BUY':
                    if ltp >= t_:
                        try:
                            self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                         order_id=connected_order_id)
                            trade['exit'] = ltp
                            trade['pl'] = running_profit
                            trade['reason'] = 'Target hit'
                            print('Exiting trade : Target hit.')
                        except Exception as e:
                            pass
                        return trade

                if trade_type == 'SELL':
                    if ltp <= t_:
                        try:
                            self.kite.session.exit_order(variety=self.kite.session.VARIETY_CO,
                                                         order_id=connected_order_id)
                            trade['exit'] = ltp
                            trade['pl'] = running_profit
                            trade['reason'] = 'Target hit'
                            print('Reason for exit: Target hit.')
                        except Exception as e:
                            pass
                        return trade

    def place_bo_order(self, transaction_type, trigger, target, stoploss, quantity=1, ):
        try:
            response = self.kite.session.place_order(tradingsymbol=self.trading_symbol,
                                                     exchange=self.exchange,
                                                     transaction_type=transaction_type,
                                                     quantity=quantity,
                                                     order_type=self.kite.session.ORDER_TYPE_LIMIT,
                                                     variety=self.kite.session.VARIETY_BO,
                                                     product=self.kite.session.PRODUCT_MIS,
                                                     price=trigger,
                                                     stoploss=stoploss,
                                                     squareoff=target)
            return response
        except Exception as e:
            print(e)

    def place_co_order(self, transaction_type, trigger, stoploss, quantity=1, ):
        if transaction_type == 'BUY':
            stoploss = trigger - stoploss

        if transaction_type == 'SELL':
            stoploss = trigger + stoploss

        try:
            response = self.kite.session.place_order(tradingsymbol=self.trading_symbol,
                                                     exchange=self.exchange,
                                                     transaction_type=transaction_type,
                                                     quantity=quantity,
                                                     order_type=self.kite.session.ORDER_TYPE_LIMIT,
                                                     variety=self.kite.session.VARIETY_CO,
                                                     product=self.kite.session.PRODUCT_MIS,
                                                     trigger_price=stoploss,
                                                     price=trigger)
            return response
        except Exception as e:
            print(e)
