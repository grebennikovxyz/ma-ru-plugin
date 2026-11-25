import type { IAuthenticateGeneric, ICredentialType, INodeProperties } from 'n8n-workflow';

export class MaRuApi implements ICredentialType {
  name = 'maRuApi';
  displayName = 'Ma-Ru Gateway';
  documentationUrl = 'https://github.com/grebennikovxyz/ma-ru-plugin#readme';
  properties: INodeProperties[] = [
    {
      displayName: 'Gateway URL',
      name: 'url',
      type: 'string',
      default: '',
      required: true,
      placeholder: 'https://mail.example.org/mcp',
    },
    {
      displayName: 'Gateway Token',
      name: 'token',
      type: 'string',
      typeOptions: { password: true },
      default: '',
      required: true,
      description: 'Bearer token configured on the Ma-Ru gateway (MA_RU_MCP_TOKEN)',
    },
  ];
  authenticate: IAuthenticateGeneric = {
    type: 'generic',
    properties: { headers: { Authorization: '=Bearer {{$credentials.token}}' } },
  };
}
