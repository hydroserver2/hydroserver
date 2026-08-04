export const E2E_PASSWORD = 'HydroServer123!'

export let users = {
  owner: {
    email: 'owner@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  editor: {
    email: 'editor@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  viewer: {
    email: 'viewer@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  limited: {
    email: 'limited@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  unaffiliated: {
    email: 'unaffiliated@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  profile: {
    email: 'profile@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
  deleteMe: {
    email: 'delete-me@uninitialized.invalid',
    password: E2E_PASSWORD,
  },
}

export let fixtures = {
  workspaces: {
    public: {
      id: 'uninitialized',
      name: 'Public',
    },
    private: {
      id: 'uninitialized',
      name: 'Private',
    },
    transfer: {
      id: 'uninitialized',
      name: 'Transfer',
    },
  },
  things: {
    public: {
      id: 'uninitialized',
      name: 'Public Thing',
      siteCode: 'UWRL',
    },
    private: {
      id: 'uninitialized',
      name: 'Private Thing',
      siteCode: 'TSC',
    },
    privatePublic: {
      id: 'uninitialized',
      name: 'Private Thing Public Workspace',
      siteCode: 'MAIN',
    },
    privateWorkspacePublic: {
      id: 'uninitialized',
      name: 'Public Thing Private Workspace',
      siteCode: 'LIB',
    },
    mutablePublic: {
      id: 'uninitialized',
      name: 'E2E Mutable Thing',
      siteCode: 'E2E-MUTABLE',
    },
  },
  datastreams: {
    public: {
      id: 'uninitialized',
      name: 'Public Datastream 1',
    },
    publicSystemMetadata: {
      id: 'uninitialized',
      name: 'Public Datastream 2',
    },
    privateVisible: {
      id: 'uninitialized',
      name: 'Private Datastream 1',
    },
    privateWorkspacePublic: {
      id: 'uninitialized',
      name: 'Private Datastream 4',
    },
  },
  metadata: {
    privateAssignedSensor: {
      id: 'uninitialized',
      name: 'Private Assigned Sensor',
    },
    publicAssignedSensor: {
      id: 'uninitialized',
      name: 'Public Assigned Sensor',
    },
    publicAssignedObservedProperty: {
      id: 'uninitialized',
      name: 'Public Assigned Observed Property',
    },
    publicAssignedProcessingLevel: {
      id: 'uninitialized',
      name: 'Public Assigned Processing Level',
    },
    publicAssignedUnit: {
      id: 'uninitialized',
      name: 'Public Assigned Unit',
    },
    systemSensor: {
      id: 'uninitialized',
      name: 'System Sensor',
    },
  },
  orchestration: {
    systemName: 'Test Streaming Data Loader',
    dataConnectionName: 'Test ETL Data Connection',
    taskName: 'Test ETL Task',
  },
}

export type E2EScenario = {
  scenarioKey: string
  users: typeof users
  fixtures: typeof fixtures
}

export function applyScenario(scenario: E2EScenario) {
  users = scenario.users
  fixtures = scenario.fixtures
}
