#!/usr/bin/env node

/**
 * Simple proxy server to get around cross domain issues
 */

const express = require('express');
const request = require('request').defaults({ strictSSL: false }); // get around bad or weird SSL certificate issues
const https = require('https');
const fs = require('fs');
const debug = require('debug')('url-proxy:server');
const normalizePort = require('normalize-port');
const nocache = require('nocache');
const morgan = require('morgan');
const validator = require('validator');
const spawn = require('child_process').spawn;

const app = module.exports = express();

/**
 * Listen
 */

let port = normalizePort(process.env.PORT || '9002');
app.set('port', port);

let byteLimit = (process.env.BYTELIMIT || 1024*1024);
// let lineLimit = (process.env.LINELIMIT || 100);

let privateKeyFn = (process.env.SSLPRIVATEKEY || '/etc/ssl/private/altius.org.key');
let certificateFn = (process.env.SSLCERTIFICATE || '/etc/ssl/certs/altius-bundle.crt');

let privateKey = fs.readFileSync(privateKeyFn);
let certificate = fs.readFileSync(certificateFn);

const options = {
  key: privateKey,
  cert: certificate
};

let server = https.createServer(options, app);
server.listen(port);
server.on('error', onError);
server.on('listening', onListening);

/**
 * Event listener for HTTP server "error" event.
 */

function onError(error) {
  if (error.syscall !== 'listen') {
    throw error;
  }

  let bind = typeof port === 'string'
    ? 'Pipe ' + port
    : 'Port ' + port;

  // handle specific listen errors with friendly messages
  switch (error.code) {
    case 'EACCES':
      console.error(bind + ' requires elevated privileges');
      process.exit(1);
      break;
    case 'EADDRINUSE':
      console.error(bind + ' is already in use');
      process.exit(1);
      break;
    default:
      throw error;
  }
}

/**
 * Event listener for HTTP server "listening" event.
 */

function onListening() {
  let addr = server.address();
  let bind = typeof addr === 'string'
    ? 'pipe ' + addr
    : 'port ' + addr.port;
  debug('Listening on ' + bind);
}

/**
 * Allow CORS
 */

function cors(req, res, next) {
  res.set('Access-Control-Allow-Origin', req.headers.origin);
  res.set('Access-Control-Allow-Methods', req.method);
  res.set('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type');
  res.set('Access-Control-Allow-Credentials', true);

  // Respond OK if the method is OPTIONS
  if (req.method === 'OPTIONS') {
    return res.send(200);
  } else {
    return next();
  }
}

/**
 * Response, CORS, cache policy and logging
 */

app.use(cors);
app.use(nocache());
app.use(morgan('combined'));

/**
 *
 * GET /?chromosome&start&bins&binSize&tabixScheme&tabixHost&dataSet&assembly&stateModel&groupShortname&saliency
 *
 */

app.get('/favicon.ico', (req, res) => {
  res.sendStatus(404);
});

app.get('/', (req, res, next) => {
  let chromosome = req.query.chromosome;
  let start = req.query.start;
  let bins = req.query.bins;
  let binSize = req.query.binSize;
  let tabixScheme = req.query.tabixScheme;
  let tabixHost = req.query.tabixHost;
  let tabixPath = req.query.tabixPath;
  let dataSet = req.query.dataSet;
  let assembly = req.query.assembly;
  let stateModel = req.query.stateModel;
  let groupShortname = req.query.groupShortname;
  let saliency = req.query.saliency;
  
  let pyArgs = [chromosome, start, bins, binSize, tabixScheme, tabixHost, tabixPath, dataSet, assembly, stateModel, groupShortname, saliency];
  let pyCmd = spawn('/home/ubuntu/recommender-proxy/recommender.py', pyArgs);
  let pyData = '';
  pyCmd.stdin.end();
  pyCmd.stdout.on('data', function(data) { pyData += data.toString(); });
  pyCmd.stdout.on('end', function() { res.write(pyData) } );
  pyCmd.on('close', (pyCmdExitCode) => {
    // check if recommender script exited with a non-zero error
    if (pyCmdExitCode !== 0) {
      res.status(400).send("Invalid input or other error");
      return;
    }
    // pipe the recommender result to the requesting client, if under the byte limit
    req
      .pipe(pyCmd.stdout)
      .on('response', function(response) {
        let contentLength = req.socket.bytesRead;
        if (contentLength > byteLimit) {
          res.status(400).send("Went over content byte limit");
        }
        /* Rewrite content header to force it to text */
        response.headers['content-type'] = 'text/plain';
      })
      .pipe(res);
  });
});
