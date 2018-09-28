from flask import Flask, send_from_directory
from flask_cors import cross_origin
from flask import request, redirect, abort
import datetime
from distributeTokens import web3

app = Flask(__name__, static_url_path="")

tokenFreq = 60

@app.route('/withdrawalRequests')
def getWithdrawalRequests():
    now = datetime.datetime.now()
    fmt = now.strftime('%Y/%m/%d/%h/%M')
    hsh = str(web3.sha3(text=fmt))
    session = request.args.get('token')
    if session != hsh:
        return hsh
    else:
        return 'Withdrawal Requests'
