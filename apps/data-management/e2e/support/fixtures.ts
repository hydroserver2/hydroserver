export const E2E_PASSWORD = 'HydroServer123!'

export const users = {
  owner: {
    email: 'owner@example.com',
    password: E2E_PASSWORD,
  },
  viewer: {
    email: 'viewer@example.com',
    password: E2E_PASSWORD,
  },
  unaffiliated: {
    email: 'unaffiliated@example.com',
    password: E2E_PASSWORD,
  },
  profile: {
    email: 'profile@example.com',
    password: E2E_PASSWORD,
  },
  deleteMe: {
    email: 'delete-me@example.com',
    password: E2E_PASSWORD,
  },
} as const

export const fixtures = {
  workspaces: {
    public: {
      id: '6e0deaf2-a92b-421b-9ece-86783265596f',
      name: 'Public',
    },
    private: {
      id: 'b27c51a0-7374-462d-8a53-d97d47176c10',
      name: 'Private',
    },
    transfer: {
      id: 'caf4b92e-6914-4449-8c8a-efa5a7fd1826',
      name: 'Transfer',
    },
  },
  things: {
    public: {
      id: '3b7818af-eff7-4149-8517-e5cad9dc22e1',
      name: 'Public Thing',
      siteCode: 'UWRL',
    },
    private: {
      id: '76dadda5-224b-4e1f-8570-e385bd482b2d',
      name: 'Private Thing',
      siteCode: 'TSC',
    },
    privateWorkspacePublic: {
      id: '819260c8-2543-4046-b8c4-7431243ed7c5',
      name: 'Public Thing Private Workspace',
      siteCode: 'LIB',
    },
    mutablePublic: {
      id: '5d4db6d5-6030-4db8-a620-23bb2d8d3f91',
      name: 'E2E Mutable Thing',
      siteCode: 'E2E-MUTABLE',
    },
  },
  datastreams: {
    public: {
      id: '27c70b41-e845-40ea-8cc7-d1b40f89816b',
      name: 'Public Datastream 1',
    },
    publicSystemMetadata: {
      id: 'dd5c60c2-a631-4e27-9aec-a59e1183861c',
      name: 'Public Datastream 2',
    },
    privateVisible: {
      id: 'e0506cac-3e50-4d0a-814d-7ae0146705b2',
      name: 'Private Datastream 1',
    },
    privateWorkspacePublic: {
      id: 'dd1f9293-ce29-4b6a-88e6-d65110d1be65',
      name: 'Private Datastream 4',
    },
  },
  orchestration: {
    systemName: 'Test Streaming Data Loader',
    dataConnectionName: 'Test ETL Data Connection',
    taskName: 'Test ETL Task',
  },
} as const
