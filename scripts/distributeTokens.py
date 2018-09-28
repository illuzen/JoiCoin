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
import csv
import datetime
import time
import pathlib
import os
import codecs
from pprint import pprint


#ethPrice = float(json.loads(requests.get('https://api.etherscan.io/api?module=stats&action=ethprice').text)['result']['ethusd'])


#provider = HTTPProvider('https://mainnet.infura.io/' + API_KEY)
#provider = HTTPProvider('https://ropsten.infura.io/' + API_KEY)
blacklist = []
testnet = True

if testnet:
    provider = HTTPProvider('http://localhost:8545')
    tokenAddr = Web3.toChecksumAddress('0x40343e2f96d9339f9a041055b9d1f449aa13ac17')
    managementAddr = Web3.toChecksumAddress('0x9d7eca44b0f9dbdb4054b26819a9ff26e8772423')

else:
    API_KEY = 'kHjl2LF2ra5jYPjrWdqB'
    provider = HTTPProvider('https://mainnet.infura.io/' + API_KEY)
    tokenAddr = Web3.toChecksumAddress('0xaa9d38d1563cca5404c7029b77e03b7fc79193df')
    managementAddr = Web3.toChecksumAddress('0x910cdc0473533aa276e668946c00bbf565eb4d9b')

web3 = Web3(provider)


# intermediate key
priv = ''
fromAddr = ''
gasPrice = int(4e9)
gasForTransfer = 60000
commission = 0.01

hashes = []


defaultPassword = b'expandinginspaceexpandingintimeexpandingincapabilities'


def getFunctionSelector(funcSig):
    # no spaces
    functionSignature = funcSig.replace(' ', '')
    # no uints, only uint256s
    functionSignature = functionSignature.replace('uint,', 'uint256,')
    functionSignature = functionSignature.replace('uint)', 'uint256)')
    return bytes.fromhex(web3.sha3(text=functionSignature).hex()[2:10])


def getFunctionEncoding(funcSig, args=[]):
    selector = getFunctionSelector(funcSig)
    argString = b''
    for arg in args:
        if web3.isAddress(arg):
            paddedArg = codecs.decode(arg[2:], 'hex')
            #paddedArg = args[i]
        elif type(arg) == int:
            paddedArg = arg.to_bytes(32, 'big')
        else:
            #paddedArg = web3.toHex(args[i])[2:]
            paddedArg = codecs.decode(arg[2:], 'hex')
        while len(paddedArg) % 32 != 0:
            paddedArg = b'\x00' + paddedArg
        argString = argString + paddedArg
#    return codecs.decode(selector + argString, 'hex')
    return selector + argString


def writeChain(contractAddr, funcSig, args=[]):
    encoding = getFunctionEncoding(funcSig, args)
    data = encoding
    #data = codecs.decode(encoding[2:], 'hex')
    nonce = web3.eth.getTransactionCount(fromAddr)
    tx = Transaction(nonce=nonce,gasprice=gasPrice,startgas=int(2e5),to=contractAddr,value=0,data=data)
    tx.sign(priv)

    raw_tx = web3.toHex(rlp.encode(tx))
    txHash = web3.eth.sendRawTransaction(raw_tx)
    print('Broadcasting', txHash)
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


def readChain(contractAddr, funcSig, args=[]):
    data = getFunctionEncoding(funcSig, args)
    nonce = web3.eth.getTransactionCount(fromAddr)
    tx = {'nonce':nonce,'gasPrice':gasPrice,'gas':int(1e6),'to':contractAddr,'from':fromAddr,'value':0,'data':data}
    return web3.eth.call(tx)


def balanceOf(addr):
    return readChain(tokenAddr, 'balanceOf(address)', [addr])


def transfer(to, amount):
    return writeChain(tokenAddr, 'transfer(address,uint256)', [to, amount])


# withdrawalRequests = [(withdrawerAddress, withdrawalAmount), ...]
def distributeTokens(withdrawalRequests):
    balance = balanceOf(fromAddr)
    balance = int.from_bytes(balance, byteorder='big')

    execution = []

    print('You have', balance, 'tokens in your address', fromAddr)

    for address, amount in tqdm(withdrawalRequests):
        try:
            if address in blacklist:
                continue
            print(address, amount)
            success, hash = transfer(address, amount)
            if success is False: raise Exception

            execution.append([address, amount, hash])
        except Exception as e:
            print(e)
            print('EXCEPTION: Skipping sending %d tokens to %s' % (amount / 1e18, address))

    # calculate fee
    try:
        totalSent = sum([x for _,x in withdrawalRequests])
        fee = int(commission * totalSent)
        success, hash = transfer(managementAddr, fee)
        execution.append([managementAddr, fee, hash])
    except Exception as e:
        print(e)
        print('EXCEPTION: Skipping sending %d tokens to managementAddr %s' % (fee / 1e18, managementAddr))


    afterBalance = balanceOf(fromAddr)
    afterBalance = int.from_bytes(afterBalance, byteorder='big')

    print('Sending complete! Remaining balance in address:', afterBalance)
    return execution


def createPrivateKey():
    return bytes([randbits(8) for _ in range(32)])


def validAddress(addr):
    print(addr)
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
    fromAddr = Web3.toChecksumAddress(fromAddr)
    nonce = web3.eth.getTransactionCount(fromAddr)
    print(nonce)
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
    print('sending address: %s' % fromAddr)

    while True:
        # report balances
        ethBalance = web3.eth.getBalance(fromAddr)
        print('fromAddr', fromAddr)

        tokenBalance = balanceOf(fromAddr)
        tokenBalance = int.from_bytes(tokenBalance, byteorder='big')
        print('eth balance of sending address:', ethBalance / 1e18)
        print('token balance of sending address:', tokenBalance / 1e18)
        if 'yes' == input('\nType yes to continue. Type anything else to check balances again\n'):
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
        for row in execution:
            writer.writerow(row)


def writeRecord(totalTokens, sendingAddress):
    with open('./payments/payments.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow([totalTokens, sendingAddress])


def matchingList(x,y):
    return len(x) == len(y) and all([x[i][0] == y[i][0] and x[i][1] == y[i][1] for i in range(len(x))])


# TODO hook up to db
def getPaymentPlan():
    return [
            ('0xc3f10b7b37fd2608e343d72f173e5b28581881b9',10)
    ]


def getPaymentPlanReal():
    url = 'localnetwork:55555/withdrawalRequests'
    resp = requests.get(url, params={}).text
    resp2 = requests.get(url, params={'token':resp})
    return resp2


if __name__ == "__main__":

    print('Collecting transaction data')
    print('Contract   :', tokenAddr)
    paymentPlan = getPaymentPlan()
    sendingAddr, totalTokens, keyfilepath = prepareFunding(paymentPlan)
    print('Sending %d tokens to %d recipients' % (totalTokens, len(paymentPlan)))
    pprint(paymentPlan)
    writeCsvPlan(paymentPlan)
    input('Press enter to execute payment plan. Press Ctrl+C to cancel.')
    execution = distributeTokens(paymentPlan)
    writeCsvExecution(execution)
    if matchingList(paymentPlan,execution) is False:
        print('WARNING: Execution list does not match payment plan')
        print(paymentPlan)
        print(execution)
    writeRecord(totalTokens, sendingAddr)
