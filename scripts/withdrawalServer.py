from flask import Flask, send_from_directory
from flask_cors import cross_origin
from flask import request, redirect, abort
import datetime
from distributeTokens import web3

app = Flask(__name__, static_url_path="")

tokenFreq = 60


def getNowBlock():
    now = datetime.datetime.now().timestamp()
    nowBlock = round(now / tokenFreq) * tokenFreq
    return nowBlock


def getToken():
    nowBlock = getNowBlock()
    hsh = web3.sha3(text=str(nowBlock))
    return hsh.hex()


@app.route('/withdrawalRequests')
def getWithdrawalRequests():
    token = getToken()
    session = request.args.get('token')
    if session != token:
        return token
    else:
        return 'Withdrawal Requests'
