export interface ExpressionDataTransformation {
  type: 'expression'
  expression: string
}

export interface LookupTableDataTransformation {
  lookupTableId: string
  type: 'lookup'
}

export type DataTransformation =
  | ExpressionDataTransformation
  | LookupTableDataTransformation

export interface MappingPath {
  targetIdentifier: string | number
  dataTransformations: DataTransformation[]
}

export interface Mapping {
  sourceIdentifier: string | number
  paths: MappingPath[]
}

export class Payload {
  name = ''
  mappings: Mapping[] = []
  extractorVariables: Record<string, string> = {}

  constructor(init?: Partial<Payload>) {
    Object.assign(this, init)
  }
}

export function addMapping(payload: Payload) {
  payload.mappings.push({
    sourceIdentifier: '',
    paths: [{ targetIdentifier: '', dataTransformations: [] }],
  })
}
