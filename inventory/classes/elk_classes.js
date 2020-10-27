'use strict'

const config = require('../config');
const { Client } = require('@elastic/elasticsearch')
require('array.prototype.flatmap').shim()

class ELKClient {
  constructor(attrs) {
    this.push_to_elk = config.elk.push_to_elk;
    this.elk_host = config.elk.host;
    this.elk_port = config.elk.port;
    if (config.elk.local) { this.elk_host = 'localhost' };
    this.elk_conn = `http://${this.elk_host}:${this.elk_port}`;
    this.elk_client = new Client({ node: this.elk_conn })
  }

  async send(attrs) {
    const dataset = attrs.json_docs
    const body = dataset.flatMap(doc => [{ index: { _index: doc.index, "_type":"type1", "_id": doc.id } }, doc])
    console.log( `Sending to ELK: ${(body.length / 2)}`, body[1].AwsService );
    const { body: bulkResponse } = await this.elk_client.bulk({ refresh: true, body })
    console.log( `Received by ELK: ${(body.length / 2)}` );
  }
}

module.exports = { ELKClient:ELKClient }
