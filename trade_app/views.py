from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
import requests
import pandas as pd
import pandas_datareader as pdr
from pandas_datareader._utils import RemoteDataError
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib import style
from django.core.exceptions import ObjectDoesNotExist
import datetime
from datetime import date
from datetime import datetime
from .forms import RegisterForm, PasswordChange, PasswordReset
from django.contrib.auth.models import User
from trade_app.models import Account, StockOrder, Position, Watchlist
from django.urls import reverse
from django.db.models import F
import yfinance as yf
from django.core.cache import cache
from django.core.cache import caches
from django.http import JsonResponse

def home(request):

    # get news headlines
    # news_url = "https://bloomberg-market-and-financial-news.p.rapidapi.com/stories/list"

    # news_query = {"template":"CURRENCY","id":"usdjpy"}

    # bloom_headers = {
    #     'x-rapidapi-host': "bloomberg-market-and-financial-news.p.rapidapi.com",
    #     'x-rapidapi-key': "3031e33fd9msh3c73fd1d3122a19p1a03abjsn0397c5598162"
    # }

    # response = requests.request("GET", news_url, headers=bloom_headers, params=news_query)
    # news_dict = response.json()
    # headline = news_dict['stories'][0:4]

    # for h in headline:
    #     dt = datetime.fromtimestamp(h['published']).strftime("%p %b %Y %H:%M:%S")
    #     dl = datetime.strptime(dt, "%p %b %Y %H:%M:%S")
    #     h['published'] = dl

    # updated_now = datetime.now()

    # # get trending tickers

    # trend_url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/get-trending-tickers"

    # trend_query = {"region":"US"}

    # yahoo_headers = {
    #     'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
    #     'x-rapidapi-key': "3031e33fd9msh3c73fd1d3122a19p1a03abjsn0397c5598162"
    # }

    # response = requests.request("GET", trend_url, headers=yahoo_headers, params=trend_query)
    # trend_dict = response.json()
    # latest_trends = trend_dict['finance']['result'][0]['quotes'][0:4]

    # # get popular watchlists

    # pop_url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/get-popular-watchlists"

    # response = requests.request("GET", pop_url, headers=yahoo_headers)
    # pop_dict = response.json()
    # pop_watch = pop_dict['finance']['result'][0]['portfolios'][0:3]

    # for p in pop_watch:
    #     p['followerCount'] = "{:,}".format(p['followerCount'])
    
    # # get movers

    # movers_url = "https://morning-star.p.rapidapi.com/market/get-movers"

    # movers_query = {"PerformanceId":"0P00001GJH"}

    # morning_headers = {
    #     'x-rapidapi-host': "morning-star.p.rapidapi.com",
    #     'x-rapidapi-key': "3031e33fd9msh3c73fd1d3122a19p1a03abjsn0397c5598162"
    # }

    # response = requests.request("GET", movers_url, headers=morning_headers, params=movers_query)
    # movers_dict = response.json()
    # actives = movers_dict['Top10']['Actives']['Securities'][0:4]
    # gainers = movers_dict['Top10']['Gainers']['Securities'][0:4]

    context = {
        # 'news': headline,
        # 'updated': updated_now,
        # 'actives': actives,
        # 'gainers': gainers,
        # 'trends': latest_trends,
        'action': 'buy',
        # 'popular': pop_watch
    }
  
    return render(request, 'trade_app/base.html', context)

def portfolio(request):
    positions = Position.objects.all().values('symbol', 'name', 'shares').filter(user__username=request.user)
    watchlist = Watchlist.objects.all().values('symbol', 'name').filter(user__username=request.user)

    if 'symbol' in request.session:
        symbol = request.session['symbol']
        name = request.session['name']
    else: 
        symbol = None
        name = None

    # sum total no. of shares

    shares = []
    for p in positions:
        shares.append(p['shares'])
    total_shares = sum(shares)

    # create cache for positions and watchlist, API key is limited to 12 requests per minute

    if cache.get('position_list') == None:
        position_prices = []

        for p in positions:
            url = "https://api.twelvedata.com/quote?symbol=%s&apikey=441febfb7f41484f965dd7dd447af6b1" % (p['symbol'])
            response = requests.request("GET", url)
            data = response.json()
            close = float(data['close'])
            last = float(data['previous_close'])
            change = (close - last) * p['shares']
            percent = (change/(close * p['shares'])) * 100
            high = data['high']
            low = data['low']
            info = [p['symbol'], p['name'], p['shares'], close, change, percent, high, low]
            position_prices.append(info)

        if len(position_prices) <= 2:
            pass
        else:
            cache.set('position_list', position_prices, 60)
    else: 
        position_prices = cache.get('position_list')

    if cache.get('watch_list') == None:
        watch_prices = []

        for w in watchlist:
            url = "https://api.twelvedata.com/time_series?symbol=%s&interval=1day&outputsize=2&apikey=441febfb7f41484f965dd7dd447af6b1" % (w['symbol'])
            response = requests.request("GET", url)
            data = response.json()
            close = float(data['values'][0]['close'])
            last = float(data['values'][1]['close'])
            change = close - last
            percent = (change/close)*100
            high = data['values'][0]['high']
            low = data['values'][0]['low']
            info = [w['symbol'], w['name'], close, change, percent, high, low]
            watch_prices.append(info)
        
        if len(watch_prices) <= 2:
            pass
        else:
            cache.set('watch_list', watch_prices, 60)

    else: 
        watch_prices = cache.get('watch_list')

    context = {
        'total': total_shares,
        'symbol': symbol,
        'name': name,
        'positions': position_prices,
        'watchlist': watch_prices
    }

    return render(request, 'trade_app/portfolio.html', context)
    
def add_to_watch (request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        name = request.POST.get('name')
        if Watchlist.objects.filter(symbol=symbol).exists():
            pass
        else:
            add = Watchlist(user=request.user, symbol=symbol, name=name)
            add.save()
    
    return HttpResponseRedirect(reverse('portfolio'))

def delete_from_watch (request, symbol):
    delete = Watchlist.objects.get(symbol=symbol)
    delete.delete()
    
    return HttpResponseRedirect('/portfolio/')


def trade(request):
    
    cash = Account.objects.values('cash_balance').filter(user__username=request.user)[0]['cash_balance']
    orders = StockOrder.objects.all().filter(user__username=request.user)

    if 'trade' in request.GET:
        # get stock info

        query = request.GET.get('trade')
        
        url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/auto-complete"
        querystring = {"region":"US","q":query}
        headers = {
            'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
            'x-rapidapi-key': "3031e33fd9msh3c73fd1d3122a19p1a03abjsn0397c5598162"
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        data = response.json()
        symbol = data['quotes'][0]['symbol'] 
        name = data['quotes'][0]['longname']
    else: 
        symbol = 'AAPL'
        name = 'Apple, Inc.' 

    # get closing price and historical data for table

    url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v3/get-historical-data"
    querystring = {"region":"US","symbol":symbol}
    headers = {
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
        'x-rapidapi-key': "3031e33fd9msh3c73fd1d3122a19p1a03abjsn0397c5598162"
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    data = response.json()
    close = data['prices'][0]['close']
    prices = data['prices'][0:7]
    last = data['prices'][1]['close']
    change = close - last
    percent = (change/close) * 100

    for p in prices:
        dt = datetime.fromtimestamp(p['date']).strftime("%B %d, %Y")
        p['date'] = dt
        p['open'] = "${:,.2f}".format(p['open'])
        p['high'] = "${:,.2f}".format(p['high'])
        p['low'] = "${:,.2f}".format(p['low'])
        p['close'] = "${:,.2f}".format(p['close'])
        p['adjclose'] = "${:,.2f}".format(p['adjclose'])


    # loop through users who own shares in the company, and then check if active user already has shares in company 

    users = []
    positions = Position.objects.values('user').filter(symbol=symbol)
    for p in positions:
        users.append(p['user'])

    # if active user has shares in company, get the amount of shares

    if request.user.id in users:
        share_count = Position.objects.filter(user__username=request.user, symbol=symbol)[0].shares
    else:
        share_count = 0

    context = {
        'symbol': symbol,
        'cash': cash,
        'name': name,
        'price': close,
        'table': prices,
        'orders': orders,
        'last': last,
        'users': users,
        'shares': share_count,
        'buy': 'buy',
        'sell': 'sell',
        'action': 'buy',
        'change': change,
        'percent': percent
    }

    return render(request, 'trade_app/trade.html', context)

def checkout(request):
    if request.method == 'POST':
        account = Account.objects.filter(user__username=request.user)
        cash = account[0].cash_balance
        symbol = request.POST.get('symbol')
        name = request.POST.get('name')
        action = request.POST.get('action')
        quantity = int(request.POST.get('quantity'))
        total = float(request.POST.get('total'))
        withdrawal = float(cash) - float(total)
        deposit = float(cash) + float(total)
        position = Position.objects.filter(user__username=request.user, symbol=symbol)
        if action == 'Buy':
            account.update(cash_balance=withdrawal)
            if position.exists():
                position.update(shares=F('shares') + quantity)
            else:
                new_position = Position(user=request.user, symbol=symbol, name=name, shares=quantity)
                new_position.save()
        else:
            account.update(cash_balance=deposit)
            if position[0].shares - quantity == 0:
                position.delete()
            else:
                position.update(shares=F('shares') - quantity)
        # save order
        order = StockOrder(user=request.user, symbol=symbol, name=name, price=total, action=action, quantity=quantity, order_date=date.today())
        order.save()
        return HttpResponseRedirect(reverse('portfolio'))
    else: 
        return HttpResponseRedirect(reverse('home'))

def reset(request):
    return render(request, 'trade_app/reset.html')

def reset_acct(request):
    Account.objects.filter(user__username=request.user).update(cash_balance=1500.00)
    Position.objects.filter(user__username=request.user).delete()
    Watchlist.objects.filter(user__username=request.user).delete()
    StockOrder.objects.filter(user__username=request.user).delete()
    # delete any sessions
    if 'symbol' in request.session:
        del request.session['symbol']
        del request.session['name']
    else: 
        pass
    return HttpResponseRedirect(reverse('home'))


# Forms

def get_registration(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('confirm-user', args=[request.POST['username']]))
    else:
        form = RegisterForm()

    return render(request, 'trade_app/registration.html', {'form': form})

def deposit(request, newuser):
    add_user = User.objects.get(username=newuser)
    new_user_account = Account(user=add_user, cash_balance=1500)
    new_user_account.save()

    context = {'user': add_user}
    return render(request, 'trade_app/registration-confirmed.html', context)

def user_account(request):
    if request.user.is_authenticated:
        username = request.user.get_username()
    else: 
        username = None

    context = {'user': username}
    return render(request, 'trade_app/user-account.html', context)

def new_pwd_confirmed(request):
    return render(request, 'trade_app/new-pwd-confirmed.html')

# get chart

def get_chart(request, ticker, name):
    # create plot
    startDate = '2015-01-01'
    endDate = str(datetime.now().strftime('%Y-%m-%d'))
    months = MonthLocator(range(1,13), bymonthday=1, interval=3)
    semi_annual = MonthLocator(range(1,13), bymonthday=1, interval=6)
    semiFmt = DateFormatter("%b '%y")
    stock_data = pdr.DataReader(ticker, 'yahoo', startDate, endDate)
    weekdays = pd.date_range(start=startDate, end=endDate)
    clean_data = stock_data['Adj Close'].reindex(weekdays)
    adj_close = clean_data.fillna(method='ffill')
    fig, ax = plt.subplots()
    ax.plot(adj_close, 'g')
    ax.xaxis.set_major_locator(semi_annual)
    ax.xaxis.set_major_formatter(semiFmt)
    ax.xaxis.set_minor_locator(months)
    ax.set_xlabel('Date') 
    ax.set_ylabel('Adj Close') 
    plt.grid(True)
    ax.autoscale_view()
    fig.autofmt_xdate()
    plt.savefig('../project_04/trade_app/static/trade_app/images/stock-chart.png')
    plt.close()

    # create sessions for portfolio to use for trade
    request.session['symbol'] = ticker
    request.session['name'] = name

    return HttpResponseRedirect(reverse('portfolio'))

