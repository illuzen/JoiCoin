module.exports = {
  // See <http://truffleframework.com/docs/advanced/configuration>
  // to customize your Truffle configuration!
  
  networks: {
    'dev': {
      host: 'localhost',
      port: 8545,
      network_id: "424242",
      before_timeout: 300,
      test_timeout: 300
   }
  }
}
};
