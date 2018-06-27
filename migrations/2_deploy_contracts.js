var SafeMath = artifacts.require('./SafeMath.sol')
var Token = artifacts.require('./Token.sol')

txConfig = {gasPrice: 4.1e9}


module.exports = (deployer, network, accounts) => {
  console.log('Deploying Libraries');
  deployer.deploy(SafeMath, txConfig).then(() => {
    console.log('Linking SafeMath')
    return deployer.link(SafeMath, [Token])
  }).then(() => {
    console.log('Deploying Token');
    return deployer.deploy(Token, txConfig);
  }).then(() => {
    console.log('Linking AccessControl, ContentManagement, Rewards')
    return deployer.link(Rewards, [PeerReview, ContentManagement])
  }).then(() => { console.log('Linking Complete') });
}
