import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import {
  PermissionAction,
  PermissionResource,
  type Workspace,
  type User,
} from '@hydroserver/client'
import { useWorkspacePermissions } from '../useWorkspacePermissions'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'

function ws(partial: Partial<Workspace>): Workspace {
  return {
    id: 'w',
    name: 'W',
    isPrivate: false,
    owner: null,
    collaboratorRole: null,
    ...partial,
  } as Workspace
}

const role = (name: string, permissions: { action: string; resource: string }[]) =>
  ({ name, permissions }) as any

const ownerWs = ws({ owner: { email: 'me@x.org', name: 'Me' } as any })
const editorWs = ws({
  id: 'ed',
  owner: { email: 'other@x.org' } as any,
  collaboratorRole: role('Editor', [
    { action: PermissionAction.Create, resource: PermissionResource.Datastream },
    { action: PermissionAction.Edit, resource: PermissionResource.Observation },
  ]),
})
const viewerWs = ws({
  id: 'vw',
  owner: { email: 'other@x.org' } as any,
  collaboratorRole: role('Viewer', [
    { action: PermissionAction.View, resource: PermissionResource.Datastream },
  ]),
})
const globalWs = ws({
  id: 'gl',
  owner: { email: 'other@x.org' } as any,
  collaboratorRole: role('Super', [
    { action: PermissionAction.Global, resource: PermissionResource.Global },
  ]),
})

function setUser(email: string, accountType = 'standard') {
  useUserStore().user = { email, accountType } as unknown as User
}

describe('useWorkspacePermissions', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('owner: can edit and create, role is Owner', () => {
    setUser('me@x.org')
    const { isOwner, canEdit, canCreateDatastream, roleName } =
      useWorkspacePermissions()
    expect(isOwner(ownerWs)).toBe(true)
    expect(canEdit(ownerWs)).toBe(true)
    expect(canCreateDatastream(ownerWs)).toBe(true)
    expect(roleName(ownerWs)).toBe('Owner')
  })

  it('editor role: can edit and create datastreams', () => {
    setUser('me@x.org')
    const { canEdit, canCreateDatastream, roleName } = useWorkspacePermissions()
    expect(canEdit(editorWs)).toBe(true)
    expect(canCreateDatastream(editorWs)).toBe(true)
    expect(roleName(editorWs)).toBe('Editor')
  })

  it('viewer role: cannot edit or create', () => {
    setUser('me@x.org')
    const { canEdit, canCreateDatastream, roleName } = useWorkspacePermissions()
    expect(canEdit(viewerWs)).toBe(false)
    expect(canCreateDatastream(viewerWs)).toBe(false)
    expect(roleName(viewerWs)).toBe('Viewer')
  })

  it('global permission grants edit and create', () => {
    setUser('me@x.org')
    const { canEdit, canCreateDatastream } = useWorkspacePermissions()
    expect(canEdit(globalWs)).toBe(true)
    expect(canCreateDatastream(globalWs)).toBe(true)
  })

  it('admin overrides a read-only role', () => {
    setUser('me@x.org', 'admin')
    const { canEdit, canCreateDatastream } = useWorkspacePermissions()
    expect(canEdit(viewerWs)).toBe(true)
    expect(canCreateDatastream(viewerWs)).toBe(true)
  })

  it('defaults to the selected workspace when no arg is passed', () => {
    setUser('me@x.org')
    useWorkspaceStore().selectedWorkspace = editorWs
    const { canEdit, roleName } = useWorkspacePermissions()
    expect(canEdit()).toBe(true)
    expect(roleName()).toBe('Editor')
  })

  it('workspaceById resolves from availableWorkspaces', () => {
    setUser('me@x.org')
    useWorkspaceStore().availableWorkspaces = [editorWs, viewerWs]
    const { workspaceById } = useWorkspacePermissions()
    expect(workspaceById('ed')?.id).toBe('ed')
    expect(workspaceById('missing')).toBeNull()
    expect(workspaceById(null)).toBeNull()
  })
})
