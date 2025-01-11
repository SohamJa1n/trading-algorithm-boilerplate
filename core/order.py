import utils.convert as convert
import pandas as pd
import core.Account as order
import utils.indicator as indicator
import api.fetch as api
from core.Rules import Rules
import core.strategies as strategies
from core.StopLossTakeProfit import StopLossTakeProfit


def indicators(account, data):
    config = api.get_settings()
    entries = {}  # datetime: close price
    exits = {}  # datetime: close price
    log = [-1]

    stoploss_takeprofit = StopLossTakeProfit()

    datetimes, opens, closes, highs, lows = convert.series_to_lists(data)

    """
    Here is a list of the data you have access to:

    - datetimes: A list of all datetimes.
    - opens: A list of opening prices.
    - closes: A list of closing prices.
    - highs: A list of high prices.
    - lows: A list of low prices.
    - data.rsi: A list of RSI values.
    - data.sma: A list of SMA values.
    - data.atr: A list of ATR values.
    - data.std_dev: A list of standard deviation values.

    All these values line up for each of your candles. For example, if you took datetimes[6], 
    closes[6] and account.rsi[6], each value would correlate to the same candle; the 7th candle.
    """

    candles = []
    for i in range(len(data.closes)):
        candle = {}
        candle["datetime"] = datetimes[i]
        candle["open"] = opens[i]
        candle["close"] = closes[i]
        candle["high"] = highs[i]
        candle["low"] = lows[i]
        candle["sma"] = data.sma[i]
        candle["rsi"] = data.rsi[i]
        candle["atr"] = data.atr[i]
        candle["std_dev"] = data.std_dev[i]

        candles.append(candle)

    def buy(entries, amount, price):
        entries = indicator.add(entries, candles[i]["datetime"], price)
        account.buy_order(candles[i]["datetime"], amount, price)
        log.append("BUY")

    def sell(exits, price):
        exits = indicator.add(exits, candles[i]["datetime"], price)
        account.sell_order(candles[i]["datetime"], price)
        log.append("SELL")

    initial_buy_amount = (
        config["account"]["baseOrderValue"] * config["multipliers"]["buyMultiplier"]
    )
    payload = {
        "z": 0,
        "initial_buy_amount": 0,
        "account": account,
    }
    rules = Rules(payload)

    for i in range(len(candles)):

        payload = {
            "initial_buy_amount": initial_buy_amount,
            "uninvested_balance": account.uninvested_balance,
            "account": account,
        }
        rules.payload = payload

        # Check if account is eligible to place a buy order (has enough uninvested capital, hasn't reached maximum amount of open positions, etc.)
        validate_response = rules.correctify()
        can_buy = False
        for value in validate_response.values():
            if value == True:
                can_buy = True
            else:
                can_buy = False
                break

        if can_buy:

            # <==================== Add your custom indicator logic below ====================>

            # Your strategy handling here

            """
            Typical handling format:

            1. Get response from your strategy
            e.g. strategy_1_response = strategies.strategy_1(params)

            2. Check if response came back with a buy signal

            3. If so, call buy() function (as seen below)

            You do not need to worry about triggering sell signals
            unless you opt not to use stop loss/take profit
  



            <========== Place a buy order: ==========>
            buy(entries, {amount}, price)

            <========== Update stoploss/takeprofit: ==========>
            stoploss_takeprofit.update(price, atr, purchase_date)

            <========== Place a sell order: ==========>
            sell(entries, price)
            ^ This will not be needed if you are using stoploss/takeprofit

            <========== Remove stoploss/takeprofit: ==========>
            stoploss_takeprofit.remove()
            """
        '''strategy_response = strategies.strategy(candle)
        if strategy_response["buy"] == True:
            buy(entries, initial_buy_amount, candles[i]["open"])
            stoploss_takeprofit.update(candles[i]["open"], candles[i]["atr"], candles[i]["datetime"])'''
        # <==================== Add your custom indicator logic above ====================>

        # Logic for checking if price has breached stoploss/takeprofit:

        if stoploss_takeprofit.values_set:
            sltp_response = stoploss_takeprofit.exit(candles[i])
            if sltp_response["sell"] == True:
                sell(exits, sltp_response["price"])
                stoploss_takeprofit.remove()

        # Logic for updating balance:

        account.open_position_amount = account.shares_owned * candles[i]["close"]
        account.balance_absolute = (
            account.uninvested_balance + account.open_position_amount
        )
        account.profit = account.balance_absolute - config["account"]["initialBalance"]

        data.ongoing_balance.append(account.balance_absolute)

    # Add entry and exit points to the graph
    entries = pd.Series(entries.values(), index=entries.keys())
    exits = pd.Series(exits.values(), index=exits.keys())

    return (
        entries,
        exits,
        stoploss_takeprofit.stoploss_regions,
        stoploss_takeprofit.takeprofit_regions,
    )