var SafeMath = artifacts.require('./SafeMath.sol')
var Token = artifacts.require('./Token.sol')
var Game = artifacts.require('./Game.sol')


let gameState = {
    BLOCK: 0,
    LEDGER: 1,
    KEY: 2
}

contract('Game', (accounts) => {

   it('plays the game', async () => {
      game = await Game.deployed()
      for (var i = 0; i < 3; i++) {
         console.log('player', accounts[i], 'exists:', await game.playerExists(accounts[i]))
      }
      await game.play(gameState.BLOCK, {from:accounts[0]})
      await game.play(gameState.LEDGER, {from:accounts[1]})

      for (var i = 0; i < 2; i++) {
         console.log('player', accounts[i], 'state:', (await game.playerState(accounts[i])).toNumber())
      }
   })
})
