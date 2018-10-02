var SafeMath = artifacts.require('./SafeMath.sol')
var Token = artifacts.require('./Token.sol')
var Game = artifacts.require('./Game.sol')

txConfig = {gasPrice: 4.1e9, gas:6e6}
trezor = '0x910CDc0473533aa276E668946c00Bbf565Eb4D9b'

module.exports = async (deployer, network, accounts) => {
   console.log('Using network', network)
   console.log('Deploying Libraries');
   deployer.deploy(SafeMath, txConfig)
   console.log('Linking SafeMath')
   deployer.link(SafeMath, [Token])
   console.log('Deploying Token');
   if (network == 'dev') {
      master = accounts[0]
   } else {
      master = trezor
   }
   console.log('with master ', master)
   deployer.deploy(Token, 1e26, master, txConfig);
   deployer.deploy(Game, [accounts[0], accounts[1]], txConfig)
}
