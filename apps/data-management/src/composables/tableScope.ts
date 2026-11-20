// Shared row-scope typing for metadata tables that support the merged "All"
// view. Kept as one identical type (rather than one per composable) so a
// table's `item`/`items` never widen to a union across its three possible
// data sources — that union previously blocked Vuetify's slot-type inference
// for `_scope`, since only the "All" data source actually sets it.
export type ItemScope = 'workspace' | 'system'
export type Scoped<T> = T & { _scope?: ItemScope }
