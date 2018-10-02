<h1> FAQs </h1>

<br> What am I doing with my life?

<br>I don't know, next question

<br> How do I run this thing?

<br>

```
ganache-cli > /dev/null &
truffle deploy --network dev
truffle test --network dev
```

Ok, so look at test/game.js to see an example of how to interact with a deployed contract. See migrations/2_deploy_contracts.js to see how to deploy a new contract (for example, start a new game). It reads the "--network" from truffle.js. Also look in the generated build/contracts folder for the contract abis. An abi is a json object that tells you how to interact with contracts. It exposes contract functions as js functions and also records the address of contracts deployed on different networks.
