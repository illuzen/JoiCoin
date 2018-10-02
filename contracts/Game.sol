pragma solidity ^0.4.19;

import "./SafeMath.sol";

contract Game {

   mapping(address => bool) public playerExists;
   mapping(address => bool) public playerPlayed;

   // 0 beats 1 beats 2 beats 0
   mapping(address => uint8) public playerState;

   constructor(address[] players) {
      for (uint i = 0; i < players.length; i++) {
         playerExists[players[i]] = true;
      }
   }

   function play(uint8 state) {
      require(playerPlayed[msg.sender] == false);
      require(playerExists[msg.sender] == true);
      require(state < 3);
      playerPlayed[msg.sender] = true;
      playerState[msg.sender] = state;
   }
}
