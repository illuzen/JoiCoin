from web3 import Web3, HTTPProvider
from ethereum.transactions import Transaction
import ethereum
import rlp
import json
from tqdm import tqdm
import requests
from web3 import Web3, HTTPProvider
from ethereum.transactions import Transaction
from ethereum.utils import privtoaddr
from eth_keyfile import create_keyfile_json, extract_key_from_keyfile
from secrets import randbits
from tqdm import tqdm
import rlp
import json
import requests
import csv
import datetime
import time
import pathlib
import os


ethPrice = float(json.loads(requests.get('https://api.etherscan.io/api?module=stats&action=ethprice').text)['result']['ethusd'])


API_KEY = ''
#provider = HTTPProvider('https://mainnet.infura.io/' + API_KEY)
provider = HTTPProvider('http://localhost:8545')
web3 = Web3(provider)
tokenAddr = ''
blacklist = []


# intermediate key
priv = ''
fromAddr = ''
gasPrice = int(4e9)
gasForTransfer = 60000
commission = 0.01

nonce = web3.eth.getTransactionCount(fromAddr)
hashes = []


defaultPassword = b'expandinginspaceexpandingintimeexpandingincapabilities'


def clean(x):
    if x == '0x':
        return 0
    return int(x, 16)


def addr(x):
    if x == '0x':
        return x
    return codecs.decode(x[-40:], 'hex')


def addrStr(x):
    return '0x' + x[-40:]


def bites(x):
    return codecs.decode(x[2:], 'hex')


def getFunctionSelector(funcSig):
    # no spaces
    functionSignature = funcSig.replace(' ', '')
    # no uints, only uint256s
    functionSignature = functionSignature.replace('uint,', 'uint256,')
    functionSignature = functionSignature.replace('uint)', 'uint256)')
    return web3.sha3(web3.toHex(functionSignature))[:10]


def getFunctionEncoding(funcSig, args=[]):
    selector = getFunctionSelector(funcSig)
    argString = ''
    for i in range(len(args)):
        paddedArg = web3.toHex(args[i])[2:]
        while len(paddedArg) % 64 != 0:
            paddedArg = '0' + paddedArg
        argString = argString + paddedArg
#    return codecs.decode(selector + argString, 'hex')
    return selector + argString


def getSuccess(contractAddr, funcSig, args=[]):
    global nonce
    encoding = getFunctionEncoding(funcSig, args)
    data = codecs.decode(encoding[2:], 'hex')
    tx = Transaction(nonce=nonce,gasprice=gasPrice,startgas=int(2e5),to=contractAddr,value=0,data=data)
    tx.sign(priv)

    raw_tx = web3.toHex(rlp.encode(tx))
    # print('funcSig', funcSig)
    # print('encoding', encoding)
    # print('args', args)
    # print('data', data)
    # print('nonce', nonce)
    # print('tx', tx.to_dict())
    # print('raw_tx', raw_tx)
    txHash = web3.eth.sendRawTransaction(raw_tx)
    print('Broadcasting', txHash)
    nonce +=1
    rcpt = web3.eth.getTransactionReceipt(txHash)
    while rcpt == None:
        try:
            rcpt = web3.eth.getTransactionReceipt(txHash)
            time.sleep(7)
        except requests.exceptions.ReadTimeout:
            print('timeout, trying again')
            pass
    if rcpt.status != 1:
        print('Tx failed', rcpt)
        return False, txHash
    print('Successful tx', txHash)
    return True, txHash


def getReturn(contractAddr, funcSig, args=[]):
    global nonce
    data = getFunctionEncoding(funcSig, args)
    #print(data, funcSig, args)
    tx = {'nonce':nonce,'gasPrice':gasPrice,'gas':int(1e6),'to':contractAddr,'value':0,'data':data}
    return web3.eth.call(tx)


def balanceOf(addr):
    return getReturn(tokenAddr, 'balanceOf(address)', [addr])


def transfer(to, amount):
    return getSuccess(tokenAddr, 'transfer(address,uint256)', [to, amount])


# withdrawalRequests = [(withdrawerAddress, withdrawalAmount), ...]
def distributeTokens(withdrawalRequests):
    balance = balanceOf(fromAddr)
    execution = []

    print('You have', balance, 'tokens in your address', fromAddr)

    for address, amount in tqdm(withdrawalRequests):
        try:
            if address in blacklist:
                continue
            success, hash = transfer(address, amount)
            if success is False: raise Exception

            execution.append([address, amount, hash])
        except Exception as e:
            print('EXCEPTION: Skipping sending %d tokens to %s' % (amount, address))


    afterBalance = balanceOf(fromAddr)
    print('Sending complete! Remaining balance in address:', afterBalance)
    return execution


def createPrivateKey():
    return bytes([randbits(8) for _ in range(32)])


def validAddress(addr):
    return (addr[:2] == '0x') and (len(addr) == 42)


def validAmount(amount):
    return type(amount) == int


def validPlan(plan):
    return all([validAddress(x) and validAmount(y) for x,y in plan])


# plan is [(address, amount), ...]
def prepareFunding(plan):

    # validate plan
    assert(validPlan(plan))

    # make private key and keyfile
    global priv
    global fromAddr
    priv = createPrivateKey()
    keyfile = create_keyfile_json(priv, defaultPassword)
    fromAddr = '0x' + privtoaddr(priv).hex()
    assert(len(fromAddr) == 42)

    keyfilepath = './keyfiles/keyfile-%d.json' % int(time.time())
    pathlib.Path('./keyfiles').mkdir(parents=True, exist_ok=True)
    with open(keyfilepath, 'w') as filo:
        json.dump(keyfile, filo)

    # sum distribution amounts, estimate gas
    totalTokens = sum([amount for (address, amount) in plan])
    gasExp = len(plan) * gasPrice * gasForTransfer / 1e18
    print('total tokens to send:', totalTokens / 1e18)
    print('total eth to send for gas:', gasExp)
    input('\n\nPlease send %f eth to address %s and press enter: ' % (gasExp, fromAddr))

    # report balances
    ethBalance = web3.eth.getBalance(fromAddr)
    tokenBalance = balanceOf(fromAddr)
    while True:
        print('eth balance of sending address:', ethBalance / 1e18)
        print('token balance of sending address:', tokenBalance / 1e18)
        if 'yes' == input('\nType yes to continue. Type anything else to check balances again'):
            break

    return fromAddr, totalTokens, keyfilepath


def writeCsvPlan(plan):
    today = datetime.datetime.today()
    with open('./payments/payments-planned-%d-%d.csv' % (today.month, today.day), 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['Recipient','TokenAmount'])
        for row in plan:
            writer.writerow(row)

def writeCsvExecution(execution):
    today = datetime.datetime.today()
    with open('./payments/payments-executed-%d-%d.csv' % (today.month, today.day), 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['Recipient','TokenAmount','TXID'])
        for row in plan:
            writer.writerow(row)

def writeRecord(totalTokens, sendingAddress):
    with open('./payments/payments.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow([totalTokens, sendingAddress])


def matchingList(x,y):
    return len(x) == len(y) and all([x[i] == y[i] for i in range(len(x))])


# TODO hook up to db
def getPaymentPlan():
    return [
            ('0xc3f10b7b37fd2608e343d72f173e5b28581881b9',10)
    ]


if __name__ == "__main__":

    print('Collecting transaction data')
    print('Contract   :', tokenAddr)
    paymentPlan = getPaymentPlan()
    sendingAddr, totalTokens, keyfilepath = prepareFunding(paymentPlan)
    print('Sending %d tokens to %d recipients' % (totalTokens, len(paymentPlan)))
    writeCsvPlan(paymentPlan)
    input('Press enter to execute payment plan. Press Ctrl+C to cancel.')
    execution = distributeTokens(paymentPlan)
    writeCsvExecution(execution)
    if matchingList(paymentPlan,execution) is False:
        print('WARNING: Execution list does not match payment plan')
    writeRecord(totalTokens, sendingAddr)
