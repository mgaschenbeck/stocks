class ReverseFromHighLow(QCAlgorithm):

    def Initialize(self):
        # Set the cash for backtest
        self.SetCash(10000)
        
        # Start and end dates for backtest
        self.SetStartDate(2018,2,1)
        self.SetEndDate(2022,5,1)
        self.SetBenchmark("SPY")

        #plotting resolution:
        self.plot_resolution=20


        # Add asset
        self.spy = self.AddEquity("SPY", Resolution.Minute).Symbol
        
        # #Create our 30 minute bars: https://www.quantconnect.com/tutorials/api-tutorials/consolidating-data-to-build-bars
        self.bar_count=0
        thirtyMinuteConsolidator = TradeBarConsolidator(timedelta(minutes=30))
        thirtyMinuteConsolidator.DataConsolidated += self.ThirtyMinuteBarHandler
        self.SubscriptionManager.AddConsolidator("SPY", thirtyMinuteConsolidator)


        # Tracking info:
        self.previous_high = None
        self.previous_low = None
        self.previous_direction = None
        self.SetWarmup(20)
        
        self.rollingWinSize=25
        
        self.priceWin = RollingWindow[float](self.rollingWinSize)

        
        self.rsi = RelativeStrengthIndex(14,MovingAverageType.Simple)
        self.RegisterIndicator(self.spy, self.rsi, thirtyMinuteConsolidator)
        self.rsiWin = RollingWindow[float](self.rollingWinSize)
        
        self.sto = Stochastic(14, 14, 3)
        self.RegisterIndicator(self.spy, self.sto, thirtyMinuteConsolidator)
        self.stoKWin = RollingWindow[float](self.rollingWinSize)
        self.stoDWin = RollingWindow[float](self.rollingWinSize)
        
        self.ema200 = ExponentialMovingAverage(200)
        self.RegisterIndicator(self.spy, self.ema200, thirtyMinuteConsolidator)
        self.ema200Win = RollingWindow[float](2)
        
        self.trade_on_next_cross_down=False
        self.trade_on_next_cross_up=False

        self.TP_ticket=None
        self.SL_ticket=None
    def OnData(self, data):
        pass
 
    def ThirtyMinuteBarHandler(self, sender, bar):
        if not self.update_and_check_indicators(bar):
            return

        if not self.Portfolio.Invested:
            #Decide to invest here
            signal = self.check_stochastic_crossover()
            if not self.trade_on_next_cross_down \
                   and self.trade_on_next_cross_up \
                   and signal==1:#buy
                orderTicket = self.SetHoldings("SPY",1.0,False,"long")
                return
            elif self.trade_on_next_cross_down \
                   and not self.trade_on_next_cross_up \
                   and signal==-1:#sell
                orderTicket = self.SetHoldings("SPY",-1.0,False,"short")
                return True
                        
            self.decide_to_invest(bar)


        #Plot example:
        self.bar_count += 1
        if self.bar_count%self.plot_resolution == 0:
             self.Plot("Overlay Plot","SandP",bar.Close)
        # if self.rsi.IsReady and self.bar_count%50 == 0:
        #      self.Plot("Overlay Plot", "rsi", self.rsi.Current.Value)
        if self.ema200.IsReady and self.bar_count%self.plot_resolution == 0:
             self.Plot("Overlay Plot", "ema", self.ema200.Current.Value)
             self.Plot("Overlay Plot", "equity",self.Portfolio.TotalPortfolioValue/10000*253)
        return

    def update_and_check_indicators(self, consolidated):
        if self.rsi.IsReady and self.sto.IsReady and self.ema200.IsReady:
            # if indicators are ready, create rolling window for them
            self.rsiWin.Add(self.rsi.Current.Value)
            self.priceWin.Add(consolidated.Close)
            self.stoKWin.Add(self.sto.StochK.Current.Value)
            self.stoDWin.Add(self.sto.StochD.Current.Value)
            self.ema200Win.Add(self.ema200.Current.Value)

            if self.rsiWin.IsReady and self.priceWin.IsReady:
                #Compute rsi local mins and max's
                self.LoadMinsAndMaxes()
                return True and self.ema200.IsReady
        return False
        
    def LoadMinsAndMaxes(self):    
        self.priceLocalMins = []
        self.priceLocalMaxs = []
        self.rsiLocalMins = []
        self.rsiLocalMaxs = []

        rsi_low = None
        rsi_high = None
        for i,r in enumerate(self.rsiWin):
            if i < 2: continue
            if i >= self.rollingWinSize-2: continue
        
            if r < self.rsiWin[i-1] and r < self.rsiWin[i-2] and \
                        r < self.rsiWin[i+1] and r < self.rsiWin[i+2]:
                if rsi_low is None or rsi_low > r: # maybe need rsi < or > 50
                    self.rsiLocalMins.append([r,i])
                    
            if r > self.rsiWin[i-1] and r > self.rsiWin[i-2] and \
                        r > self.rsiWin[i+1] and r > self.rsiWin[i+2]:
                if rsi_high is None or rsi_high < r:
                    self.rsiLocalMaxs.append([r,i])

    def check_stochastic_crossover(self):
        if self.stoKWin[1]<self.stoDWin[1] and self.stoKWin[0]>self.stoDWin[0]:
            #buy signal:
            return 1
        elif self.stoKWin[1]>self.stoDWin[1] and self.stoKWin[0]<self.stoDWin[0]:
            #buy signal:
            return -1
        else:
            return 0
            
    def decide_to_invest(self,bar):
        #Look for shorts higher highs on RSI, lower lows for price
        if self.ema200Win[0]>bar.Close:
            if (not self.trade_on_next_cross_down) or self.trade_on_next_cross_up:
                #Check for high on RSI:
                for lm,lm_ind in self.rsiLocalMaxs:
                    #New high on RSI!
                    if self.rsi.Current.Value > lm:
                        #Check for lower lows on price
                        if bar.Close < self.priceWin[lm_ind]:
                            #We will trade, trigger:
                            self.trade_on_next_cross_down=True
                            self.trade_on_next_cross_up=False
                            return True
        #Look for longs
        else:
            #Check for low on RSI:
            if (self.trade_on_next_cross_down) or not self.trade_on_next_cross_up:
                for lm,lm_ind in self.rsiLocalMins:
                    if self.rsi.Current.Value < lm:
                        #Check for higher highs on price
                        if bar.Close > self.priceWin[lm_ind]:
                            #We will trade, trigger:
                            self.trade_on_next_cross_down=False
                            self.trade_on_next_cross_up=True
                            return True
        return False
                                
    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            order = self.Transactions.GetOrderById(orderEvent.OrderId)
            if order.Tag == "long":
                fill_price = orderEvent.FillPrice
                quantity = orderEvent.FillQuantity
                profit_price = fill_price*1.05
                loss_price = fill_price*.995
                self.TP_ticket = self.LimitOrder("SPY",-quantity,profit_price)
                self.SL_ticket = self.StopMarketOrder("SPY",-quantity,loss_price)
                self.trade_on_next_cross_down=False
                self.trade_on_next_cross_up=False
                #self.Log(f"Long:{fill_price},{quantity},{profit_price},{loss_price}")
            elif order.Tag == "short":
                fill_price = orderEvent.FillPrice
                quantity = orderEvent.FillQuantity
                profit_price = fill_price*.995
                loss_price = fill_price*1.005
                self.TP_ticket=self.LimitOrder("SPY",-quantity,profit_price)
                self.SL_ticket=self.StopMarketOrder("SPY",-quantity,loss_price)
                self.trade_on_next_cross_down=False
                self.trade_on_next_cross_up=False  
                #self.Log(f"Short:{fill_price},{quantity},{profit_price},{loss_price}")
            #self.Log(str(type(self.TP_ticket)))

            if order.Type == OrderType.Limit or order.Type == OrderType.StopMarket:
                self.Transactions.CancelOpenOrders("SPY")
                self.Liquidate()