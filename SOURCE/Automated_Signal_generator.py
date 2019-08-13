# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 18:04:29 2019

@author: kennedy
"""
import os
from STOCK import stock, loc
import pandas as pd
from oandapyV20 import API
#from mpl_finance import candlestick2_ohlc
pd.options.mode.chained_assignment = None
import numpy as np
import multiprocessing
from threading import Thread
import threading
from datetime import datetime
import lightgbm as lgb
import matplotlib.pyplot as plt
from Preprocess import process_time
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.ensemble import (AdaBoostRegressor, #Adaboost regressor
                              RandomForestRegressor, #Random forest regressor
                              GradientBoostingRegressor, #Gradient boosting
                              BaggingRegressor, #Bagging regressor
                              ExtraTreesRegressor) #Extratrees regressor

from DCollector import Path, Runcollector
## SIGNAL GENERATOR --> MACD, BOLLINGER BAND, RSI, etc
  
#Moving average signals
class signalStrategy(object):
    def __init__(self):
        return
    
    def ls_STOK(self):
      '''
      :Return:
        List of stock in dataset
      '''
      DIR_OBJ = os.listdir()
      STOK_list_ = []
      for x in range(len(DIR_OBJ)):
        STOK_list_.append(DIR_OBJ[x].strip('.csv'))
        
      return STOK_list_
  
    def MA_signal(self, STK_data, ema = None, sma = None, period_alpha = None,
                  period_beta = None):
      '''
      :Params:
        :STK_data: Stock data
        :ema: defaul is None. if True, function uses ema instead of sma
        :sma: default is None. if True, fucntion uses sma instead of ema
        :period_alpha: first moving average
        :period_beta: first moving average
      :Complexity: Time: O(N) | Space: O(1)
      '''
      stock_data = stock(STK_data)
      df = stock_data.OHLC()
      if sma and ema:
        raise ValueError('sma and ema cannot be true at same time')
      elif ema:
        assert period_alpha < period_beta, 'Ensure period_alpha is less than period beta'
        alpha = stock_data.ema(stock_data.Close, period_alpha)
        beta = stock_data.ema(stock_data.Close, period_beta)
        df['signal'] = np.where(beta > alpha, 0, 1)
        df[f'EMA {period_alpha}'] = alpha
        df[f'EMA {period_beta}'] = beta
      elif sma:
        assert period_alpha < period_beta, 'Ensure period_alpha is less than period beta'
        alpha = stock_data.sma(stock_data.Close, period_alpha)
        beta = stock_data.sma(stock_data.Close, period_beta)
        df['signal'] = np.where(beta > alpha, 0, 1)
        df[f'SMA {period_alpha}'] = alpha
        df[f'SMA {period_beta}'] = beta
      #return siganl
      return df
      
    ##RSI signal
    def RSI_signal(self, STK_data, period, lw_bound, up_bound):
      '''
      :Arguments:
        df: stock data
      :Return type:
        signal
      :Complexity: Time: O(N*log N) | Space: O(1)
      '''
      stock_data = stock(STK_data)
      df = stock_data.OHLC()
      #get signal
      #1--> indicates buy position
      #0 --> indicates sell posotion
      rsi = np.array(stock_data.WilderRSI(stock_data.c, period))
      rsi = np.nan_to_num(rsi)
      signal = np.zeros_like(rsi)
      for ii in range(len(signal)):
          if rsi[ii] >= up_bound:
              signal[ii:] = 1
          elif rsi[ii] <= lw_bound:
              signal[ii:] = 0
      df['RSI'] = rsi
      df['signal'] = signal
      print('*'*40)
      print('RSI Signal Generation completed')
      print('*'*40)
      return df
      
    #RSI Signal
    def macd_crossOver(self, STK_data, fast, slow, signal):
      '''
      :Argument:
        MACD dataframe
      :Return type:
        MACD with Crossover signal
      :Complexity: Time: O(N) | Space: O(1)
      '''
      stock_data = stock(STK_data)
      OHLC = stock_data.OHLC()
      df = stock_data.MACD(fast, slow, signal)
      try:
        assert isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)
        #dataframe
        if isinstance(df, pd.Series):
          df = df.to_frame()
        else:
          pass
        #1--> indicates buy position
        #0 --> indicates sell posotion
        df['signal'] = np.where(df.MACD > df.MACD_SIGNAL, 1, 0)
        df = pd.concat([OHLC, df], axis = 1)
      except IOError as e:
        raise('Dataframe required {}' .format(e))
      finally:
        print('*'*40)
        print('MACD signal generated')
        print('*'*40)
      return df
    
    #SuperTrend Signal
    def SuperTrend_signal(self, STK_data, multiplier, period):
      '''
      :Argument:
        SuperTrend dataframe
      :Return type:
        Super trend signal
      :Complexity: Time: O(N) | Space: O(1)
      '''
      stock_data = stock(STK_data)
      #--Call superTrend function
      OHLC = stock_data.OHLC()
      df = stock_data.SuperTrend(STK_data, multiplier, period)
      try:
        assert isinstance(df, pd.DataFrame) or isinstance(df, pd.Series)
        #dataframe
        if isinstance(df, pd.Series):
          df = df.to_frame()
        else:
          pass
        #1--> indicates buy position
        #0 --> indicates sell posotion
        df = df.fillna(0)
        df['signal'] = np.where(stock_data.Close >= df.SuperTrend, 1, 0)
        df = pd.concat([OHLC, df], axis = 1)
      except IOError as e:
        raise('Dataframe required {}' .format(e))
      finally:
        print('*'*40)
        print('SuperTrend Signal generated')
        print('*'*40)
      return df
    
    #Bollinger band signal
    def bollinger_band_signal(self, STK_data, period, deviation):
        '''
        :Argument:
            df: stock data
        :Return type:
            :bollinger band signal
        :Complexity: Time: O(N*log N) | Space: O(1)
        '''
        stock_data = stock(STK_data)
        Close = np.array(stock_data.Close)
        OHLC = stock_data.OHLC()
        dfbol = stock_data.Bolinger_Band(period, deviation)
        dfbol = dfbol.fillna(value = 0)
        assert isinstance(dfbol, pd.DataFrame) or isinstance(dfbol, pd.Series)
        #dataframe
        if isinstance(dfbol, pd.Series):
            dfbol = dfbol.to_frame()
        #get signal
        #1--> indicates buy position
        #0 --> indicates sell posotion
#        df['signal'] = np.zeros(df.shape[0])
        Upperband = np.array(dfbol.Upper_band)
        Lowerband = np.array(dfbol.Lower_band)
        signal = np.zeros(dfbol.shape[0])
        for ii in range(len(Close)):
            if Close[ii] >= Upperband[ii]:
                signal[ii:] = 1
            elif Close[ii] <= Lowerband[ii]:
                signal[ii:] = 0
        df = pd.concat([OHLC, dfbol], axis = 1)
        df['signal'] = signal
        print('*'*40)
        print('Bollinger Signal Generation completed')
        print('*'*40)
        return df

#Trading Algorithm
#This is the position--> BUY, SELL, HOLD
class Signal(object):
    def __init__(self):
        return
    
    def tradingSignal(self, STK_data, RSI = None, MACD = None, Bollinger_Band = None, SuperTrend = None, MA = None, strategy = None):
        '''
        STRATEGIES
        ========================
        [1] MA CROSS-OVER
        [2] BOLLINGER BAND
        [3] MACD
        [4] RSI
        [5] SUPER TREND
        [6] MA vs SUPER_TREND
        [7] MA vs MACD
        [8] MA vs RSI
        [9] MA vs BOLLINGER BAND
        [11] BOLLINGER BAND vs MACD
        [22] BOLLINGER BAND vs RSI
        [33] BOLLINGER vs SUPERTREND
        [44] RSI vs SUPER TREND
        [55] MOVING AVERAGE vs BOLLINGER BAND vs MACD
        [66] MOVING AVERAGE vs BOLLINGER BAND vs RSI
        [77] MOVING AVERAGE vs BOLLINGER BAND vs SUPER TREND
        ---------------------
        [88] MOVING AVERAGE vs RSI vs MACD
        [99] MOVING AVERAGE vs RSI vs SUPERTREND
        [111] MOVING AVERAGE vs MACD vs SUPERTREND
        [222] MACD vs SUPERTREND vs RSI
        [333] MACD vs SUPERTREND vs BOLLINGER BAND
        ----------------------
        [444] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI
        [555] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs SUPER TREND
        [666] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI vs SUPER TREND
        ------------------------------------------------------------------------
        :Arguments:
            :MACD:
                dataframe containing MACD signal
            :Bollinger_Band:
                dataframe containing Bollinger band signal
            :RSI:
                dataframe containing RSI signal
            :Return Type:
                Buy Sell or Hold signal
        '''
        stock_data = stock(STK_data)
        OHLC = stock_data.OHLC()
        columns = ['Open', 'High', 'Low', 'Close', 'signal']
        #--define strategy
        #--MA---
        if strategy == '1':
            Moving_avg = MA.signal
            MA['Position'] = ''
            for ii in range(MA.shape[0]):
                if Moving_avg[ii] == 1:
                    MA.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0:
                    MA.Position[ii] = 'SELL'
            return MA
        #-- Bollinger Band---
        elif strategy == '2':
            BB_signal = Bollinger_Band.signal.values
            Bollinger_Band['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if BB_signal[ii] == 1:
                    Bollinger_Band.Position[ii] = 'BUY'
                elif BB_signal[ii] == 0:
                    Bollinger_Band.Position[ii] = 'SELL'
            return Bollinger_Band
        #-- MACD ----
        elif strategy == '3':
            MACD_signal = MACD.signal.values
            MACD['Position'] = ''
            for ii in range(MACD.shape[0]):
                if MACD_signal[ii] == 1:
                    MACD.Position[ii] = 'BUY'
                elif MACD_signal[ii] == 0:
                    MACD.Position[ii] = 'SELL'
            return MACD
        #-- RSI----
        elif strategy == '4':
            RSI_signal = RSI.signal.values
            RSI['Position'] = ''
            for ii in range(RSI.shape[0]):
                if RSI_signal[ii] == 1:
                    RSI.Position[ii] = 'BUY'
                elif RSI_signal[ii] == 0:
                    RSI.Position[ii] = 'SELL'
            return RSI
        #-- SuperTrend_Signal ---
        elif strategy == '5':
            SuperTrend_Signal = SuperTrend.signal.values
            SuperTrend['Position'] = ''
            for ii in range(SuperTrend.shape[0]):
                if SuperTrend_Signal[ii] == 1:
                    SuperTrend.Position[ii] = 'BUY'
                elif SuperTrend_Signal[ii] == 0:
                    SuperTrend.Position[ii] = 'SELL'
            return SuperTrend
        #--MA vs SUPER_TREND--
        elif strategy == '6':
            SuperTrend_Signal = SuperTrend.signal.values
            Moving_avg = MA.signal
            OHLC['Position'] = ''
            for ii in range(OHLC.shape[0]):
                if Moving_avg[ii] == 1 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            return OHLC
        #-- MA vs MACD ----
        elif strategy == '7':
            Moving_avg = MA.signal
            MACD_signal = MACD.signal.values
            OHLC['Position'] = ''
            for ii in range(OHLC.shape[0]):
                if Moving_avg[ii] == 1 and MACD_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and MACD_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--MA vs RSI--
        elif strategy == '8':
            Moving_avg = MA.signal
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(Moving_avg.shape[0]):
                if Moving_avg[ii] == 1 and RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and RSI_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired], axis = 1)
            return OHLC
        #--- MA vs BOLLINGER BAND ---
        elif strategy == '9':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            OHLC['Position'] = ''
            for ii in range(Moving_avg.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            return OHLC
        #-- BOLLINGER BAND vs MACD
        elif strategy == '11':
            BB_signal = Bollinger_Band.signal.values
            MACD_signal = MACD.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if BB_signal[ii] == 1 and MACD_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif BB_signal[ii] == 0 and MACD_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--BOLLINGER BAND vs RSI--
        elif strategy == '22':
            BB_signal = Bollinger_Band.signal.values
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if BB_signal[ii] == 1 and RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif BB_signal[ii] == 0 and RSI_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired], axis = 1)
            return OHLC
        #--BOLLINGER vs SUPERTREND --
        elif strategy == '33':
            BB_signal = Bollinger_Band.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if BB_signal[ii] == 1 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif BB_signal[ii] == 0 and SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            return OHLC
        #--RSI vs SUPER TREND --
        elif strategy == '44':
            RSI_signal = RSI.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(SuperTrend_Signal.shape[0]):
                if RSI_signal[ii] == 1 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif RSI_signal[ii] == 0 and SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs MACD --
        elif strategy == '55':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            MACD_signal = MACD.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    MACD_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    MACD_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs RSI --
        elif strategy == '66':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    RSI_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs SUPER TREND --
        elif strategy == '77':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            return OHLC
        #--MOVING AVERAGE vs RSI vs MACD --
        elif strategy == '88':
            Moving_avg = MA.signal
            RSI_signal = RSI.signal.values
            MACD_signal = MACD.signal.values
            OHLC['Position'] = ''
            for ii in range(Moving_avg.shape[0]):
                if Moving_avg[ii] == 1 and RSI_signal[ii] == 1 and\
                    MACD_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and RSI_signal[ii] == 0 and\
                    MACD_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired, macdRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs RSI vs SUPERTREND --
        elif strategy == '99':
            Moving_avg = MA.signal
            RSI_signal = RSI.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(Moving_avg.shape[0]):
                if Moving_avg[ii] == 1 and RSI_signal[ii] == 1 and\
                    SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and RSI_signal[ii] == 0 and\
                    SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs MACD vs SUPERTREND --
        elif strategy == '111':
            Moving_avg = MA.signal
            MACD_signal = MACD.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(Moving_avg.shape[0]):
                if Moving_avg[ii] == 1 and MACD_signal[ii] == 1 and\
                    SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and MACD_signal[ii] == 0 and\
                    SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--MACD vs SUPERTREND vs RSI --
        elif strategy == '222':
            MACD_signal = MACD.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(RSI_signal.shape[0]):
                if MACD_signal[ii] == 1 and SuperTrend_Signal[ii] == 1 and\
                    RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif MACD_signal[ii] == 0 and SuperTrend_Signal[ii] == 0 and\
                    RSI_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired, macdRequired], axis = 1)
            return OHLC
        #--MACD vs SUPERTREND vs BOLLINGER BAND --
        elif strategy == '333':
            MACD_signal = MACD.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            BB_signal = Bollinger_Band.signal.values
            OHLC['Position'] = ''
            for ii in range(MACD_signal.shape[0]):
                if MACD_signal[ii] == 1 and SuperTrend_Signal[ii] == 1 and\
                    BB_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif MACD_signal[ii] == 0 and SuperTrend_Signal[ii] == 0 and\
                    BB_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI --
        elif strategy == '444':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            MACD_signal = MACD.signal.values
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    MACD_signal[ii] == 1 and RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    MACD_signal[ii] == 0 and RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired, macdRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs MACD vs SUPER TREND --
        elif strategy == '555':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            MACD_signal = MACD.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    MACD_signal[ii] == 1 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    MACD_signal[ii] == 0 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
        #--MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI vs SUPER TREND--
        elif strategy == '666':
            Moving_avg = MA.signal
            BB_signal = Bollinger_Band.signal.values
            MACD_signal = MACD.signal.values
            RSI_signal = RSI.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(BB_signal.shape[0]):
                if Moving_avg[ii] == 1 and BB_signal[ii] == 1 and\
                    MACD_signal[ii] == 1 and RSI_signal[ii] == 1 and\
                    SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif Moving_avg[ii] == 0 and BB_signal[ii] == 0 and\
                    MACD_signal[ii] == 0 and RSI_signal[ii] == 0 and\
                    SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired, macdRequired], axis = 1)
            return OHLC
        elif strategy == '777':
            MACD_signal = MACD.signal.values
            RSI_signal = RSI.signal.values
            OHLC['Position'] = ''
            for ii in range(MACD_signal.shape[0]):
                if MACD_signal[ii] == 1 and RSI_signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif MACD_signal[ii] == 0 and RSI_signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            rsiRequired = RSI.drop([x for x in columns], axis = 1)
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, rsiRequired, macdRequired], axis = 1)
            return OHLC
        elif strategy == '888':
            MACD_signal = MACD.signal.values
            SuperTrend_Signal = SuperTrend.signal.values
            OHLC['Position'] = ''
            for ii in range(MACD_signal.shape[0]):
                if MACD_signal[ii] == 1 and SuperTrend_Signal[ii] == 1:
                    OHLC.Position[ii] = 'BUY'
                elif MACD_signal[ii] == 0 and SuperTrend_Signal[ii] == 0:
                    OHLC.Position[ii] = 'SELL'
                else:
                    OHLC.Position[ii] = 'HOLD'
            macdRequired = MACD.drop([x for x in columns], axis = 1)
            OHLC = pd.concat([OHLC, macdRequired], axis = 1)
            return OHLC
    
    def main(self, path, strategy, STOCK, DEVIATION = None, MULTIPLIER = None, PERIOD = None, LOWER_BOUND = None,
             UPPER_BOUND = None, MIDLINE = None, FAST = None, SLOW = None, SIGNAL = None, TIMEFRAME = None,
             PERIOD_ALPHA = None, PERIOD_BETA = None):
        '''
        :param:
            :strategy: select a startegy to signal signal 
            INDICATOR SIGNALS
            ========================
            [x] MOVING AVERAGE
            [x] BOLLINGER BAND
            [X] MACD
            [X] RSI
            [X] SUPERTREND
            ========================
            STRATEGIES
            ========================
            [1] MA CROSS-OVER
            [2] BOLLINGER BAND
            [3] MACD
            [4] RSI
            [5] SUPERTREND
            -----------------------
            [6] MA vs SUPERTREND
            [7] MA vs MACD
            [8] MA vs RSI
            [9] MA vs BOLLINGER BAND
            X[11] BOLLINGER BAND vs MACD
            [22] BOLLINGER BAND vs RSI
            [33] BOLLINGER vs SUPERTREND
            X[44] RSI vs SUPERTREND
            ------------------------
            [55] MOVING AVERAGE vs BOLLINGER BAND vs MACD
            [66] MOVING AVERAGE vs BOLLINGER BAND vs RSI
            [77] MOVING AVERAGE vs BOLLINGER BAND vs SUPERTREND
            ---------------------
            [88] MOVING AVERAGE vs RSI vs MACD
            [99] MOVING AVERAGE vs RSI vs SUPERTREND
            [111] MOVING AVERAGE vs MACD vs SUPERTREND
            [222] MACD vs SUPERTREND vs RSI
            [333] MACD vs SUPERTREND vs BOLLINGER BAND
            ----------------------
            [444] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI
            [555] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs SUPERTREND
            [666] MOVING AVERAGE vs BOLLINGER BAND vs MACD vs RSI vs SUPERTREND
            ------------------------------
            [777] MACD vs RSI
            [888] MACD vs SUPERTREND
        :return type:
            signal saved to prediction table
        '''
        from os.path import join
        if not os.path.exists(path+"/PREDICTED/STRATEGY_{}/{}".format(str(strategy), TIMEFRAME)):
            os.makedirs(path+ "/PREDICTED/STRATEGY_{}/{}".format(str(strategy), TIMEFRAME))

        datapath = join(path, 'DATASETS/{}/'.format(STOCK))
        #-------get the data we need------------------
        df = loc.read_csv(join(datapath, STOCK + '_{}'.format(TIMEFRAME) + str('.csv')))
        stock_data = stock(df)
        if strategy == '1':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            signal = Signal().tradingSignal(df, MA = MA_alphbeta, strategy = strategy)
        elif strategy == '2':
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            signal = Signal().tradingSignal(df, Bollinger_Band = df_BB, strategy = strategy)
        elif strategy == '3':
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            signal = Signal().tradingSignal(df, MACD = df_MACD, strategy = strategy)
        elif strategy == '4':
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, RSI = df_RSI, strategy = strategy)
        elif strategy == '5':
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, SuperTrend = df_STrend, strategy = strategy)
        elif strategy == '6':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, SuperTrend = df_STrend, MA = MA_alphbeta, strategy = strategy)
        elif strategy == '7':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            signal = Signal().tradingSignal(df, MACD = df_MACD, MA = MA_alphbeta, strategy = strategy)
        elif strategy == '8':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, RSI = df_RSI, MA = MA_alphbeta, strategy = strategy)
        elif strategy == '9':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            signal = Signal().tradingSignal(df, Bollinger_Band = df_BB, MA = MA_alphbeta, strategy = strategy)
        elif strategy == '11':
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            signal = Signal().tradingSignal(df, Bollinger_Band= df_BB, MACD = df_MACD, strategy = strategy)
        elif strategy == '22':
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, Bollinger_Band= df_BB, RSI = df_RSI, strategy = strategy)
        elif strategy == '33':
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, Bollinger_Band= df_BB, SuperTrend= df_STrend, strategy = strategy)
        elif strategy == '44':
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, RSI= df_RSI, SuperTrend= df_STrend, strategy = strategy)
        elif strategy == '55':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, MACD=df_MACD, strategy = strategy)
        elif strategy == '66':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, RSI=df_RSI, strategy = strategy)
        elif strategy == '77':
            MA_alphbeta =signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, SuperTrend=df_STrend, strategy = strategy)
            #---------------------------------
        #--MOVING AVERAGE vs RSI vs MACD
        elif strategy == '88':
            MA_alphbeta =signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, RSI = df_RSI, MACD = df_MACD, strategy = strategy)
        #--MOVING AVERAGE vs RSI vs SUPERTREND
        elif strategy == '99':
            MA_alphbeta =signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, RSI= df_RSI, SuperTrend=df_STrend, strategy = strategy)
        #--MOVING AVERAGE vs MACD vs SUPERTREND
        elif strategy == '111':
            MA_alphbeta =signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, MACD= df_MACD, SuperTrend=df_STrend, strategy = strategy)
        #--MACD vs SUPERTREND vs RSI
        elif strategy == '222':
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, MACD= df_MACD, SuperTrend=df_STrend, RSI=df_RSI, strategy = strategy)
        #--MACD vs SUPERTREND vs BOLLINGER BAND
        elif strategy == '333':
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            signal = Signal().tradingSignal(df, MACD=df_MACD, SuperTrend=df_STrend, Bollinger_Band= df_BB, strategy = strategy)
        #---
        elif strategy == '444':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, MACD=df_MACD, RSI=df_RSI, strategy = strategy)
        elif strategy == '555':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, MACD=df_MACD, SuperTrend=df_STrend, strategy = strategy)
        elif strategy == '666':
            MA_alphbeta = signalStrategy().MA_signal(stock_data, ema = True, period_alpha=PERIOD_ALPHA, period_beta=PERIOD_BETA)
            df_BB = signalStrategy().bollinger_band_signal(df, PERIOD, deviation = DEVIATION)
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MA= MA_alphbeta, Bollinger_Band= df_BB, MACD=df_MACD, RSI=df_RSI, SuperTrend=df_STrend, strategy = strategy)
        elif strategy == '777':
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_RSI = signalStrategy().RSI_signal(df, PERIOD, lw_bound = LOWER_BOUND, up_bound = UPPER_BOUND)
            signal = Signal().tradingSignal(df, MACD=df_MACD, RSI=df_RSI, strategy = strategy)
        elif strategy == '888':
            df_MACD = signalStrategy().macd_crossOver(df, FAST, SLOW, SIGNAL)
            df_STrend = signalStrategy().SuperTrend_signal(df, MULTIPLIER, PERIOD)
            signal = Signal().tradingSignal(df, MACD=df_MACD, SuperTrend=df_STrend, strategy = strategy)
        else:
            pass
    
        print('*'*40)
        print('Signal generation completed...')
        print('*'*40)
        print('Saving file')
        #---strategy selection-----
        loc.set_path(path+ '/PREDICTED/STRATEGY_{}/{}'.format(str(strategy), TIMEFRAME))
        signal.to_csv('{}'.format(STOCK)+ '.csv', mode='w')



class Run(Runcollector):
    def __init__(self, path, strategy, STOCKLIST, DEVIATION, MULTIPLIER, PERIOD, LOWER_BOUND,\
                 UPPER_BOUND, MIDLINE, FAST, SLOW, SIGNAL, TIMEFRAME,\
                 PERIOD_ALPHA, PERIOD_BETA):
        
        self.path = path
        self.strategy = strategy
        self.STOCKLIST = STOCKLIST
        self.DEVIATION = DEVIATION
        self.MULTIPLIER = MULTIPLIER
        self.PERIOD = PERIOD
        self.LOWER_BOUND = LOWER_BOUND
        self.UPPER_BOUND = UPPER_BOUND
        self.MIDLINE = MIDLINE
        self.FAST = FAST
        self.SLOW = SLOW
        self.SIGNAL = SIGNAL
        self.TIMEFRAME = TIMEFRAME
        self.PERIOD_ALPHA = PERIOD_ALPHA
        self.PERIOD_BETA = PERIOD_BETA
        
        with open(self.path['mainPath'] +'/DOCS/token.txt') as tk:
            token = tk.readline().strip()
            self.client = API(access_token = token)
            
        Path(self.path)
        super().__init__(self.path, self.path['start'], self.path['end'], self.client, self.TIMEFRAME)
        
        try:
            if self.STOCKLIST is None:
                raise ValueError('Incorrect stock name\n Enter atleast one stock name or stock/fx pair')
            else:
                thread = []
                for ii, stkList in enumerate(self.STOCKLIST):
                    thread.append(multiprocessing.Process(target = self.runMain, args = [stkList]))
                for trd in thread:
                    trd.daemon = True
                    trd.start()
                for st_trd in thread:
                    st_trd.join()
        except Exception:
            raise ValueError('Thread unable to start')
            
    def runSignal(self, stkname):
        return Signal().main(path = self.path['mainPath'], strategy = self.strategy, STOCK = stkname, DEVIATION = self.DEVIATION, MULTIPLIER = self.MULTIPLIER, PERIOD = self.PERIOD, LOWER_BOUND = self.LOWER_BOUND,\
              UPPER_BOUND = self.UPPER_BOUND, MIDLINE = self.MIDLINE, FAST = self.FAST, SLOW = self.SLOW, SIGNAL = self.SIGNAL, TIMEFRAME = self.TIMEFRAME,\
              PERIOD_ALPHA = self.PERIOD_ALPHA, PERIOD_BETA = self.PERIOD_BETA)
        
    def runMain(self, stkname):
        self.stkname = stkname
        import time
        begin = time.time()
        if not self.path:
            raise ValueError('path not provided') 
        elif not self.strategy:
            raise ValueError('Strategy not define')
        elif not self.DEVIATION:
            raise ValueError('DEVIATION required')
        elif not self.PERIOD:
            raise ValueError('PERIOD required')
        elif not self.LOWER_BOUND:
            raise ValueError('LOWER_BOUND required')
        elif not self.UPPER_BOUND:
            raise ValueError('UPPER_BOUND required')
        elif not self.FAST:
            raise ValueError('FAST required')
        elif not self.SLOW:
            raise ValueError('SLOW required')
        elif not self.SIGNAL:
            raise ValueError('SIGNAL required')
        elif not self.TIMEFRAME:
            raise ValueError('TIMEFRAME required')
        elif not self.PERIOD_ALPHA:
            raise ValueError('PERIOD_ALPHA required')
        elif not self.PERIOD_BETA:
            raise ValueError('PERIOD_BETA required')
        else:
            self.runSignal(self.stkname)
        print(f'End time {time.time() - begin}')
        print(datetime.today())
        print('program running in background')

#%% main script 
if __name__ == '__main__':
    import multiprocessing
    import time
    #---------GLOBAL SETTINGS-------------------
    path = '/home/kenneth/Documents/GIT_PROJECTS/AI-Signal-Generator'
    STRATEGY = '111'
    DEVIATION = MULTIPLIER = 2
    PERIOD = 20
    #---------MA SETTINGS--------------
    PERIOD_ALPHA = 10
    PERIOD_BETA = 20
    #--------RSI_SETTINGS------------------------
    LOWER_BOUND = 30
    UPPER_BOUND = 70
    MIDLINE = 0
    FILLCOLOR = 'skyblue'
    #--------MACD SETTINGS-----------------------
    FAST = 12
    SLOW = 26
    SIGNAL = 9
    TIMEFRAME = 'H1'
    instrument = ['EUR_USD', 'GBP_USD', 'AUD_CAD', 'AUD_USD',
                 'BTC_USD', 'EUR_CAD', 'EUR_GBP', 'EUR_NZD',
                 'NZD_USD']
      
    Run(path = path, strategy = STRATEGY, STOCKLIST = instrument, DEVIATION = DEVIATION, PERIOD = PERIOD, LOWER_BOUND = LOWER_BOUND,\
        UPPER_BOUND = UPPER_BOUND, MIDLINE = MIDLINE, FAST = FAST, SLOW = SLOW, SIGNAL = SIGNAL, TIMEFRAME = TIMEFRAME,\
        PERIOD_ALPHA = PERIOD_ALPHA, PERIOD_BETA = PERIOD_BETA, timer = 1800)

    

    
    
    