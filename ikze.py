from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtWidgets import QApplication,QMessageBox,QMainWindow,QWidget,QVBoxLayout
from datetime import datetime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sqlite3
import os,sys
import csv
import yfinance as yf
import requests
from matplotlib.figure import Figure
import pandas as pd

dataDB=[]
f_path=os.getcwd()
# Connect to an SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect(f_path+'\\mBnk.db')
curs = conn.cursor()


def get_cash():
    """
       Get all cash entries from dB and add them
       :return: float [sum]
       """
    curs.execute("SELECT * from aktywa where ticker=\"cash\"")
    sum=0
    for ii in curs:
        sum+=float(ii[2])
    return round(sum,2)

def getCur(cur,oper):
    """
       Get exchange rate of given currency and operation type
       :return: float [rate]
       """
    url=''
    if oper=="buy":
        if cur=="USD":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/USD/last/1/?format=json"
        elif cur == "GBP":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/GBP/last/1/?format=json"
        elif cur=="EUR":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/EUR/last/1/?format=json"
    else:
        if cur == "USD":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/USD/last/1/?format=json"
        elif cur == "GBP":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/GBP/last/1/?format=json"
        elif cur == "EUR":
            url = "https://api.nbp.pl/api/exchangerates/rates/C/EUR/last/1/?format=json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if oper=="buy":
            rate = data['rates'][0]['ask']
        else:
            rate = data['rates'][0]['bid']
        print(f"Rate {oper} {cur}: {rate}")
        return round(rate,4)
    else:
        print("Error connecting to remote host.")
        return 1
    
def get_data():
    """
    Getting of data from DB and adding them to global list dataDB
    :return: None
    """
    global dataDB
    dataDB=[]
    ticKERS=get_tickers()
    for tic2 in ticKERS:
        curs.execute("SELECT * from aktywa where ticker=\"" + str(tic2) + "\" ORDER BY id DESC LIMIT 1")
        for inx in curs:
            dataDB.append({'id':str(inx[0]), 'date':inx[1] , 'ticker':inx[6] , 'name':inx[7], 'cur': inx[4],'curs':str(inx[2]),'vol':str(inx[3]),'val':str(inx[5])})

def get_rate(tic,curr):
    """
       Get current rate for given ticker and currency
       :return: float [rate]
       """
    if tic=='cash':
        cash=0
        curs.execute("SELECT * from aktywa where ticker=\"cash\" ORDER BY id DESC LIMIT 1")
        rtv=curs.fetchone()
        cash=rtv[2]
        return cash
    ticker = yf.Ticker(tic)
    data = ticker.history(period="1d")
    if data.empty:
        print("Brak danych – upewnij się, że symbol jest poprawny.")
        QMessageBox.warning(None, "Ostrzeżenie", f"Nieporawny symbol tickera: {tic}",QMessageBox.Yes | QMessageBox.No,QMessageBox.No)
        return 1
    current_price = data["Close"].iloc[-1]
    if tic=="SGLN.L":
        current_price/=100
    print(f"Current price {tic}: {current_price:.2f} {curr}")
    return round(current_price,2)

def init():
    """
       Initialize dB
       :return: None
       """
    curs.execute('''CREATE TABLE IF NOT EXISTS aktywa
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date text, curs real , vol real, walut text, value real, ticker text, name text)''')

def expo():
    """
       Export dB to csv file
       :return: None
       """
    data=curs.execute("SELECT * FROM aktywa")
    c_date = datetime.now()
    f_date = c_date.strftime("%d-%m-%Y_%H_%M")
    file2 = f_path+'\\db' + f_date + '.csv'
    with open(file2, 'w', newline='') as f:
        writer = csv.writer(f,delimiter=';')
        writer.writerow(['ID', 'DATA','Kurs','Wolumen','Waluta','Wartość','Ticker','Nazwa'])
        #writer.writerows(data)

        for ii in data:
            line=[]
            line.append(str(ii[0]))
            line.append(ii[1])
            line.append(str(ii[2]).replace('.',','))
            line.append(str(ii[3]).replace('.',','))
            line.append(ii[4])
            line.append(str(ii[5]).replace('.',','))
            line.append(ii[6])
            line.append(ii[7])
            writer.writerow(line)
    QMessageBox.information(None, "Informacja", "Zapis do pliku zakończony pomyślnie.", QMessageBox.Ok)

def get_tickers():
    """
       get tickers id from dB
       :return: list[str]
       """
    data=curs.execute("SELECT DISTINCT ticker FROM aktywa")
    rtv=[]
    for ii in data:
        rtv.append(ii[0])
    return rtv

def get_names():
    """
       Get names of tickers from DB
       :return: list[str]
       """
    data=curs.execute("SELECT DISTINCT name FROM aktywa")
    rtv=[]
    for gg in data:
        rtv.append(gg[0])
    return rtv

def delete(idd):
    """
       Delete entry from DB
       :return: None
   """
    curs.execute("DELETE FROM aktywa WHERE id = ?", (idd,))

def update_entry(id_x,**kwargs):
    """
    Updates entry(id_x) to DB
    :return: None
   """
    expr=''
    for ii,jj in kwargs.items():
        expr+=str(ii)+"="+'\''+str(jj)+'\','
    expr=expr.rstrip(',')
    up_c=f"UPDATE aktywa set {expr} where ID = {id_x}"
    curs.execute(up_c)

class WykresCanvas(FigureCanvas):
    def __init__(self,a, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100)

        super().__init__(self.fig)
        self.setParent(parent)
        if a=="1":
            self.plot_chart()
        else:
            self.draw_pie()

    def chart_data(self,ticF, typD):
        """
            Gets data for charts
            :return: list[str]
           """
        # data=[{'date':'2025-07-01','val':'0.5'},{'date':'2025-07-03','val':'1'}]
        data = []
        data0 = curs.execute("SELECT * FROM aktywa where ticker=\"" + ticF + "\"")
        data1 = {}
        for indx in data0:
            if typD == "Kurs":
                data1 = {'date': indx[1], 'val': indx[2]}  # (data)
            elif typD == "Wart":
                data1 = {'date': indx[1], 'val': indx[5]}
            data.append(data1)
        return data

    def draw_pie(self):
        """
            Draws PIE
            :return: None
           """
        ticKERS = get_tickers()
        labe = get_names()
        labe.append('PLN')
        vall = []
        sizes = []
        sum = 0
        for tic in ticKERS:
            if tic!="cash":
                curs.execute("SELECT * from aktywa where ticker=\"" + str(tic) + "\" ORDER BY id DESC LIMIT 1")
                for entry in curs:
                    sum += float(entry[5])
                    vall.append(float(entry[5]))
        vall.append(float(win.lineE_cash.text()))
        sum+=float(win.lineE_cash.text())
        for ii in vall:
            sizes.append(ii * 100 / sum)
        explode = (0.15,0)
        for i in range(len(sizes)-2):
            explode=explode+(0,)
        ax = self.fig.add_subplot(211)
        ax.pie(sizes, explode=explode, labels=ticKERS, autopct='%1.1f%%',
               shadow=True, startangle=140)
        ax.set_title('Udział funduszy w portfelu')
        ax.axis('equal')
        opis = ""
        for ii in range(0, len(ticKERS)):
            opis += ticKERS[ii] + "-" + labe[ii] +" WARTOŚĆ:"+str(vall[ii])+ " [PLN]\n"
        self.fig.text(0.5,0.02,opis,ha='center',fontsize=10)

    def plot_chart(self):
        """
            Draws Chart
            :return: None
           """
        ticc = win.comboBox_2.currentText()#lista_tic
        typ2 = win.comboBox.currentText()
        ax = self.fig.add_subplot(111)
        if typ2=="Wart":
            dataCh = self.chart_data(ticc, "Wart")
            df2 = pd.DataFrame(dataCh)
            df2['date'] = pd.to_datetime(df2['date'], format="%d-%m-%Y %H:%M")
            df2['val'] = pd.to_numeric(df2['val'])
            ax.bar(df2['date'], df2['val'], width=4.45, color='lightblue', label=ticc + " wartość")

        elif typ2 == "Oba":
            dataCh = self.chart_data(ticc, "Kurs")
            df = pd.DataFrame(dataCh)
            df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y %H:%M")
            df['val'] = pd.to_numeric(df['val'])
            dataCh2 = self.chart_data(ticc, "Wart")
            df2 = pd.DataFrame(dataCh2)
            df2['date'] = pd.to_datetime(df2['date'], format="%d-%m-%Y %H:%M")
            df2['val'] = pd.to_numeric(df2['val'])
            ax.bar(df2['date'], df2['val'], width=0.15, color='lightblue', label=ticc + " wartość")

            ax2=ax.twinx()
            ax2.plot(df['date'], df['val'], marker='o', color='green', label=ticc + " kurs")
            lin1,lab1=ax.get_legend_handles_labels()
            lin2, lab2 = ax2.get_legend_handles_labels()
            ax2.legend(lin1+lin2,lab1+lab2,loc='upper left')
        else:
            dataCh = self.chart_data(ticc, typ2)
            df = pd.DataFrame(dataCh)
            df['date'] = pd.to_datetime(df['date'], format="%d-%m-%Y %H:%M")
            df['val'] = pd.to_numeric(df['val'])
            ax.plot(df['date'], df['val'], marker='o', color='green', label=ticc)
            ax.legend()
            if typ2=="Kurs":
                beg_val, c_val = compare_rate(ticc)
                if c_val < 0:
                    kol = 'red'
                else:
                    kol = 'green'
                if beg_val < 0:
                    kol2 = 'red'
                else:
                    kol2 = 'green'
                self.fig.text(0.5, 0.2, str(c_val) + "%", ha='center', fontsize=14, color=kol)
                self.fig.text(0.5, 0.29, "Od poczatku:" + str(round(beg_val, 2)) + "%", ha="center", color=kol2)
        ax.set_title(typ2 + ' w czasie')
        ax.set_xlabel('Data')
        ax.set_ylabel(typ2 + ' (PLN)')
        ax.grid(True)

class SecondWindow(QWidget):
    """
    SecondWindow Class responsible for GUI operation for charts window
    """
    def __init__(self,par):
        super().__init__()
        self.setWindowTitle("Wykres")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        self.canvas = WykresCanvas(par,self)
        layout.addWidget(self.canvas)
        self.canvas.draw()
        self.setLayout(layout)
    
def commit_db(dat,n_curs,vol,tick,name,curr,oper):
    if oper=="buy":
        if curr=="USD":
            value=round(getCur("USD","buy")*float(n_curs)*float(vol),2)
        elif curr=="EUR":
            value=round(getCur("EUR","buy")*float(n_curs)*float(vol),2)
        elif curr=="GBP":
            value = round(getCur("GBP","buy") * float(n_curs) * float(vol), 2)
        else:
            value=round(float(n_curs)*float(vol),2)
    else:
        if curr=="USD":
            value=round(getCur("USD","sell")*float(n_curs)*float(vol),2)
        elif curr=="EUR":
            value=round(getCur("EUR","sell")*float(n_curs)*float(vol),2)
        elif curr=="GBP":
            value = round(getCur("GBP","sell") * float(n_curs) * float(vol), 2)
        else:
            value=round(float(n_curs)*float(vol),2)
    if tick=="cash":
        val=get_cash()
        value=float(n_curs)+val
    task=(dat,n_curs,vol,curr,value,tick,name)
    curs.execute("INSERT INTO aktywa(date,curs,vol,walut,value ,ticker,name) VALUES (?,?,?,?,?,?,?)",task)
    print("Added to db #",curs.lastrowid)
    conn.commit()

def compare_rate(tic):
    """
    Compares rates for ticker
    :return: list[float :f_begin,float: current]
    """
    curs.execute("SELECT curs FROM aktywa WHERE ticker = \""+tic+"\" ORDER BY id ASC")
    start = curs.fetchone()
    curs.execute("SELECT curs from aktywa where ticker=\"" + tic + "\" ORDER BY id DESC")
    last = curs.fetchone()
    divide=last[0]/start[0]
    f_begin=round(100 * (divide - 1), 3) #change in percent from begin
    curs.execute("SELECT curs from aktywa where ticker=\"" + tic + "\" ORDER BY id DESC LIMIT 2 ")
    change=curs.fetchall()
    current=[]
    divide=1
    if len(change)>1:
        for indx in change:
            current.append(indx[0])
        divide=current[0]/current[1]
    return [f_begin,round(100*(divide-1), 3)]


class MainWindow(QMainWindow):
    """
    MainWindow Class responsible for GUI operation
    """

    def get_last_id(self):
        """
           Gets last entry from dB
           :return: Str
           """
        curs.execute("SELECT *,max(id) from aktywa")
        return str(curs.fetchone()).split(',')

    def up_cur(self):
        """
           Updates (commits to dB) all tickers, also updates the GUI
           :return: None
           """
        cur_date = datetime.now()
        date_formated = cur_date.strftime("%d-%m-%Y %H:%M")
        ticKERS = get_tickers()
        for tic in ticKERS:
            curs.execute("SELECT * from aktywa where ticker=\"" + tic + "\" ORDER BY id DESC LIMIT 1")
            for row in curs:
                n_curs = get_rate(row[6], row[4])
                voL = row[3]
                tick = row[6]
                name = row[7]
                currency = row[4]
                if tick!='cash':
                    commit_db(date_formated, n_curs, voL, tick, name, currency,"sell")
        self.list_()
        total2 = float(self.lineE_cash.text()) + float(self.lineE_suma.text()) - float(self.lineE_cost.text())
        self.lineE_all.setText(str(round(total2, 2)))
        net=float(self.lineE_suma.text()) - float(self.lineE_paid.text())
        resu=0
        if float(self.lineE_paid.text())!=0:
            resu = float(self.lineE_suma.text()) / float(self.lineE_paid.text()) - 1
        if resu >= 0:
            self.label_wynik.setStyleSheet("color: green;")
        else:
            self.label_wynik.setStyleSheet("color: red;")
        sum2 = "Wynik:" + str(round(resu * 100, 2)) + "%, " + str(net)
        win.label_wynik.setText(sum2)

    def list_(self):
        """
           Updates QTableWidget
           :return: None
           """
        get_data()
        d_len = len(dataDB)
        self.tabela.setRowCount(d_len)
        row = 0
        suma=0
        for dBB in dataDB:
            self.tabela.setItem(row, 0, QtWidgets.QTableWidgetItem(dBB["id"]))
            self.tabela.setItem(row, 1, QtWidgets.QTableWidgetItem(dBB["date"]))
            self.tabela.setItem(row, 2, QtWidgets.QTableWidgetItem(dBB["ticker"]))
            self.tabela.setItem(row, 3, QtWidgets.QTableWidgetItem(dBB["name"]))
            self.tabela.setItem(row, 4, QtWidgets.QTableWidgetItem(dBB["cur"]))
            elem=dBB["curs"]
            font = QFont()
            font.setBold(True)
            change=compare_rate(dBB["ticker"])[1]
            item0=QtWidgets.QTableWidgetItem(elem)
            item0.setFont(font)
            if change>=0:
                item0.setForeground(QBrush(QColor("green")))
            else:
                item0.setForeground(QBrush(QColor("red")))
            self.tabela.setItem(row, 5,item0)
            self.tabela.setItem(row, 6, QtWidgets.QTableWidgetItem(dBB["vol"]))
            self.tabela.setItem(row, 7, QtWidgets.QTableWidgetItem(dBB["val"]))
            if dBB["ticker"]!="cash":
                item = QtWidgets.QTableWidgetItem(str(compare_rate(dBB["ticker"])))
                item.setFont(font)
                suma += float(dBB["val"])
                self.tabela.setItem(row, 8, item)
            else:
                item=QtWidgets.QTableWidgetItem("[ ]")
                item.setFont(font)
                self.tabela.setItem(row, 8, item)
            row = row + 1

        self.lineE_suma.setText(str(round(suma,2)))

    def open_f(self):
        """
           Reads data from 'additional' file
           :return: None
           """
        file2 = f_path + '\\dane.txt'
        with open(file2, 'r', newline='\n') as f:
            r_lines = f.readlines()#.split(';')
            first_line=r_lines[0].strip()
            last_line=r_lines[-1].split(';')
            dat = last_line[0]
            value = last_line[1]
            self.paid=last_line[2]
            oplaty=last_line[3]
            self.cash=value
            self.lineE_cash.setText(value)
            self.lineE_cost.setText(oplaty)
            self.label_cash.setText(f"Gotówka(stan na {dat})")
            self.label_limit.setText(f"Limit wpłat na rok {str(datetime.now().year)}={first_line}")

    def save_f(self):
        """
        Writes data to 'additional' file
        :return: None
        """
        file2 = f_path + '\\dane.txt'
        wplaty=str(round(get_cash(),2))
        with open(file2, 'a', encoding="utf-8",newline='') as f:
            if self.lineE_cash.text()!=self.cash:
                d1=datetime.today()
                dat =d1.date()
                tim=str(d1.hour)+":"+str(d1.minute)
                wart=self.lineE_cash.text()
                s_line='\n'+str(dat)+"_"+tim+";"+wart+";"+wplaty+";"+self.lineE_cost.text()
                f.write(s_line)

    def add_entry(self):
        """
          Adds entry to db basing on data from GUI
          :return: None
        """
        curr_date = datetime.now()
        date_formated = curr_date.strftime("%d-%m-%Y %H:%M")
        tic = self.lineE_tick.text()
        name = self.lineE_name.text()
        n_vol = self.lineE_vol.text()
        n_currency = self.lineE_cur.text()
        n_curs = self.lineE_curs.text()
        self.comboBox_2.addItems([tic])
        commit_db(date_formated, float(n_curs), float(n_vol), tic, name, n_currency,"buy")
        self.list_()
        conn.commit()

    def del_entry(self):
        """
        Deletes entry from DB
        :return: None
        """
        index = int(self.lineE_id.text())
        reply = QMessageBox.question(self, "Pytanie", f"Czy usunąć wpis nr {index}?", QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)

        if reply == QMessageBox.Yes:
            delete(index)
            conn.commit()
        else:
            return
        self.list_()

    def stats(self):
        """
        Opens MessageBox with stats for current ticker based on GUI
        :return: None
        """
        tick = self.comboBox_2.currentText()
        data = curs.execute("SELECT date,MIN(curs) FROM aktywa where ticker=\"" + tick + "\"")
        datmin = data.fetchone()
        data = curs.execute("SELECT date,MAX(curs) FROM aktywa where ticker=\"" + tick + "\"")
        datmax = data.fetchone()
        data = curs.execute("SELECT date,curs FROM aktywa where ticker=\"" + tick + "\" ORDER BY ID ASC LIMIT 1")
        data_beg = data.fetchone()
        data = curs.execute("SELECT date,curs FROM aktywa where ticker=\"" + tick + "\" ORDER BY ID DESC LIMIT 1")
        data_cur = data.fetchone()
        data = curs.execute("SELECT DISTINCT(name),walut FROM aktywa where ticker=\"" + tick + "\"")
        data_combine = data.fetchone()
        msg=f"Statystyki dla {data_combine[0]}:Kurs[{data_combine[1]}]\nPoczątek data:{data_beg[0]},watość: {str(data_beg[1])}\nMin data:{datmin[0]},watość: {str(datmin[1])}\nMax data:{datmax[0]},watość: {str(datmax[1])}\naktualna data:{data_cur[0]},watość: {str(data_cur[1])}"
        delta=100*(round(data_cur[1]/data_beg[1]-1,3))
        msg+=f"\nRóżnica od początku:{str(round(delta,2))}%"
        QMessageBox.information(None, "Informacja", msg, QMessageBox.Ok)

    def update_entry(self):
        """
        Saves entry to DB basing on GUI settings
        :return: None
        """
        curr_date = datetime.now()
        date_formatted = curr_date.strftime("%d-%m-%Y %H:%M")
        voL = self.lineE_vol.text()
        n_currency = self.lineE_cur.text()
        ij = int(self.lineE_id.text())
        tick=self.lineE_tick.text()
        n_curs = get_rate(tick,n_currency) #float(self.lineE_curs.text())
        if n_currency == "USD":
            ff = getCur("USD","sell")
        elif n_currency == "EUR":
            ff = getCur("EUR","sell")
        elif n_currency == "GBP":
            ff = getCur("GBP","sell")
        else:
            ff = 1
        cur_value = round(n_curs * float(voL) * ff, 2)
        update_entry(ij, date=date_formatted, curs=n_curs, vol=voL, value=cur_value)
        self.list_()
        conn.commit()

    def update_gui_by_row(self):
        """
        Updates gui for currently selected row from QTableWidget
        :return: None
        """
        sel_row=self.tabela.currentRow()
        item_id=self.tabela.item(sel_row, 0).text()
        item_tic=self.tabela.item(sel_row, 2).text()
        item_name = self.tabela.item(sel_row, 3).text()
        item_curr = self.tabela.item(sel_row, 4).text()
        item_curs = self.tabela.item(sel_row, 5).text()
        item_vol = self.tabela.item(sel_row, 6).text()
        self.lineE_cur.setText(item_curr)
        self.lineE_curs.setText(item_curs)
        self.lineE_vol.setText(item_vol)
        self.lineE_name.setText(item_name)
        self.lineE_tick.setText(item_tic)
        self.lineE_id.setText(item_id)
        self.comboBox_2.setCurrentText(item_tic)
        self.lineE_vol.setFocus()

    def deposit(self):
        """
        Adds 'cash' entry to DB
        :return: None
        """
        dateT=self.lineE_data.text()
        cash=self.lineE_pay.text()
        summ=float(cash)+float(self.lineE_paid.text())
        self.lineE_paid.setText(str(round(summ, 2)))
        total=float(self.lineE_cash.text())+float(cash)
        self.lineE_cash.setText(str(total))
        commit_db(dateT, cash, 1, "cash", "Gotówka", "PLN", "buy")

    def __init__(self):
        """
        Initialization of variables (after loading from - loadUi)
        """
        super(MainWindow,self).__init__()
        loadUi("ikze.ui",self)
        self.cash=0.0
        self.paid=0.0
        USD_rate = getCur("USD","buy")
        EUR_rate = getCur("EUR","buy")
        GBP_rate = getCur("GBP","buy")
        kur=f"Kurs kupna PLN/USD:{USD_rate} PLN/GBP:{GBP_rate} PLN/EUR:{EUR_rate}"
        self.label_kurs.setText(kur)
        self.b_odsw.setStyleSheet("background-color: #aaff00")
        self.b_del.setStyleSheet("background-color: #ff634e")
        self.b_update.setStyleSheet("background-color: #4effff")
        self.b_stats.setStyleSheet("background-color: #938bff")
        self.tabela.setColumnWidth(0,12)
        self.tabela.setColumnWidth(1, 115)
        self.tabela.setColumnWidth(2, 93)
        self.tabela.setColumnWidth(3, 205)
        self.tabela.setColumnWidth(4, 48)
        self.tabela.setColumnWidth(5, 48)
        self.tabela.setColumnWidth(6, 30)
        self.tabela.setColumnWidth(7, 55)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.list_()
        self.b_add.clicked.connect(self.add_entry)
        self.b_wyk.clicked.connect(lambda: self.open_chart("1"))
        self.b_udzial.clicked.connect(lambda: self.open_chart("2"))
        self.b_del.clicked.connect(self.del_entry)
        self.b_update.clicked.connect(self.update_entry)
        self.b_odsw.clicked.connect(self.up_cur)
        self.b_stats.clicked.connect(self.stats)
        self.b_expo.clicked.connect(expo)
        self.b_payin.clicked.connect(self.deposit)
        self.tabela.clicked.connect(self.update_gui_by_row)
        self.opened_windows = []
        self.comboBox_2.addItems(get_tickers())
        entry=self.get_last_id()
        #print(entry)
        if entry[0]!='(None':
            self.lineE_id.setText(entry[0][1:])
            self.lineE_cur.setText(entry[4].strip('\'')[2:])
            self.lineE_curs.setText(entry[2].strip())
            self.lineE_name.setText(entry[7].strip('\'')[2:])
            self.lineE_tick.setText(entry[6].strip('\'')[2:])
            self.lineE_vol.setText(entry[3].strip())
        sum=get_cash()
        self.lineE_paid.setText(str(round(sum,2)))
        c_date = datetime.now()
        f_date = c_date.strftime("%d-%m-%Y %H:%M")
        self.lineE_data.setText(f_date)

    def open_chart(self,a):
        """
        Opens charts
        :return: None
        """
        wind = SecondWindow(a)
        self.opened_windows.append(wind)
        wind.show()

"""
Main Loop
"""
init()
app = QApplication(sys.argv)
win = MainWindow()
widget = QtWidgets.QStackedWidget()
widget.addWidget(win)
widget.setWindowTitle('IKZE manager')

widget.setFixedHeight(400)
widget.setFixedWidth(850)
widget.show()
win.open_f()
netto=round(float(win.lineE_suma.text())-float(win.lineE_paid.text()),2)
if win.lineE_paid.text()=="0":
    res=0
else:
    res = float(win.lineE_suma.text())/float(win.lineE_paid.text())-1
if res >= 0:
    win.label_wynik.setStyleSheet("color: green;")
else:
    win.label_wynik.setStyleSheet("color: red;")
suma="Wynik:" + str(round(res*100,2))+ "%, " + str(netto)
win.label_wynik.setText(suma)
total=float(win.lineE_cash.text())+float(win.lineE_suma.text())-float(win.lineE_cost.text())

win.lineE_all.setText(str(round(total,2)))
try:
    sys.exit(app.exec_())
except:
    print("Exiting")
    win.save_f()
    conn.close()
