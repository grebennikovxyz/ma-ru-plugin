const assert = require('node:assert/strict');
const { test } = require('node:test');
const { MaRu } = require('../dist/nodes/MaRu/MaRu.node.js');
const { MaRuApi } = require('../dist/credentials/MaRuApi.credentials.js');
const node = new MaRu();
function context(items, toolReply, url = 'https://gateway.example/mcp', tolerate = false) {
  const calls = [];
  return {
    calls,
    getInputData: () => items,
    getNode: () => ({ name: 'Mail.ru' }),
    continueOnFail: () => tolerate,
    getNodeParameter: (key, i) => items[i][key],
    getCredentials: async () => ({ url, token: 'fixture' }),
    helpers: {
      httpRequestWithAuthentication: async (name, options) => {
        assert.equal(name, 'maRuApi');
        assert.equal(options.disableFollowRedirect, true);
        calls.push(options.body);
        const { method, id } = options.body;
        if (method === 'initialize') return { id, result: { protocolVersion: '2025-11-25' } };
        if (method === 'notifications/initialized') return;
        return { id, result: toolReply };
      },
    },
  };
}
test('n8n package registers its node, credentials and all operations', () => {
  const pkg = require('../package.json');
  assert.equal(require('../' + pkg.n8n.nodes[0]).MaRu, MaRu);
  assert.equal(require('../' + pkg.n8n.credentials[0]).MaRuApi, MaRuApi);
  assert.equal(new MaRuApi().properties[1].typeOptions.password, true);
  assert.equal(new Set(node.description.properties[0].options.map((o) => o.value)).size, 26);
});
test('poll keeps receipt and never auto-acknowledges', async () => {
  const ctx = context(
    [
      {
        operation: 'poll_new',
        poll_new_feed: 'morning',
        poll_new_account: 'qa@example.org',
        poll_new_folder: 'INBOX',
        poll_new_limit: 1,
        poll_new_include_existing: false,
      },
    ],
    { content: [{ type: 'text', text: '{"receipt":"batch","messages":[]}' }] },
  );
  const [items] = await node.execute.call(ctx);
  assert.equal(items[0].json.result.receipt, 'batch');
  assert.deepEqual(
    ctx.calls.map((r) => r.method),
    ['initialize', 'notifications/initialized', 'tools/call'],
  );
  assert.deepEqual(ctx.calls[2].params.arguments, {
    account: 'qa@example.org',
    feed: 'morning',
    folder: 'INBOX',
    limit: 1,
    include_existing: false,
  });
});
test('batch results keep item links and singleton lists', async () => {
  const ctx = context(
    [
      { operation: 'list_folders', list_folders_account: 'a@example.org' },
      { operation: 'list_folders', list_folders_account: 'b@example.org' },
    ],
    { content: [{ type: 'text', text: '{"folder":"INBOX"}' }] },
  );
  const [items] = await node.execute.call(ctx);
  assert.deepEqual(
    items.map((x) => x.pairedItem.item),
    [0, 1],
  );
  assert.deepEqual(items[1].json.result, [{ folder: 'INBOX' }]);
});
test('failed tools never become successes and insecure URLs are rejected before auth', async () => {
  const ctx = context(
    [{ operation: 'list_accounts' }],
    { isError: true, content: [{ type: 'text', text: 'Access denied' }] },
    undefined,
    true,
  );
  assert.match((await node.execute.call(ctx))[0][0].json.error, /Access denied/);
  const bad = context([{ operation: 'list_accounts' }], {}, 'http://bad.example/mcp', true);
  assert.match((await node.execute.call(bad))[0][0].json.error, /HTTPS/);
  assert.equal(bad.calls.length, 0);
});
test('structured list results retain their array shape', async () => {
  const folders = [{ folder: 'INBOX' }];
  const ctx = context([{ operation: 'list_folders', list_folders_account: 'a@example.org' }], {
    structuredContent: { result: folders },
  });
  const [items] = await node.execute.call(ctx);
  assert.deepEqual(items[0].json.result, folders);
});
