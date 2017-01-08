var casper = require('casper').create();
var meme = casper.cli.args.length >= 1 ?  casper.cli.args[0] : 'xzibit';
var ttop = casper.cli.args.length >= 2 ?  casper.cli.args[1] : ' ';
var tbot = casper.cli.args.length >= 3 ?  casper.cli.args[2] : 'yo';
var maxt = casper.cli.args.length >= 4 ? +casper.cli.args[3] : 30000;

casper.options.timeout       = maxt;
casper.options.onTimeout     = function() { this.exit(1); };
casper.options.onWaitTimeout = function() { this.exit(2); };

casper.start('http://imgur.com/memegen', function() {
    this.waitForSelector('#defaults .selection', function() {
        this.click('#defaults .selection');
        this.sendKeys('#defaults .options .filter', meme);
        this.waitForSelector('#defaults .options .item', function() {
            this.click('#defaults .options .item');
            this.waitForSelector('#spinner[style*="display: none;"]', function() {
                this.sendKeys('#top-text-input', ' ');
                this.sendKeys('#bottom-text-input', ' ');
                this.sendKeys('#top-text-input', ttop);
                this.sendKeys('#bottom-text-input', tbot);
                this.click('#meme-save-button');
            });
        });
    });
});

casper.page.onUrlChanged = function(url) {
    if (url.indexOf('imgur') != -1
        && url.substr(0, 24) != 'http://imgur.com/memegen'
    ) {
        casper.echo(url);
        casper.exit(0);
    }
};

casper.run(function() { });
