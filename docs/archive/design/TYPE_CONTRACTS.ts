/**
 * DESIGN REFERENCE, NOT A DROP-IN IMPLEMENTATION.
 * Adapt types to existing Ajv/Pydantic and source position conventions AFTER inspecting real repo.
 */
export type StudyState =
  | 'planned' | 'hypothesized' | 'in_progress' | 'observed' | 'validated' | 'mixed' | 'unknown';
export type RelationType =
  | 'sequence' | 'depends_on' | 'parallel' | 'tests' | 'measures'
  | 'supports' | 'activates' | 'inhibits' | 'feedback' | 'association';
export type RenderRoute = 'text_structured' | 'asset_composite' | 'image_first' | 'strict_scientific';
export interface SourceRef {
  id: string;
  documentHash: string;
  blockId: string;
  utf16Range: readonly [number, number];  // use existing project indexing convention
  excerpt: string;
  verification: 'approved_user_brief' | 'verified_exact' | 'pending' | 'rejected';
}
export interface ScientificEntity {
  id: string;
  name: string;
  scientificKind: string;
  sourceRefIds: string[];
}
export interface ScientificRelation {
  id: string;
  fromId: string;
  toId: string;
  type: RelationType;
  evidenceState: StudyState;
  sourceRefIds: string[];
  critical: boolean;
  conditionLabelId?: string;
}
export interface ApprovedLabel {
  id: string;
  exactText: string;
  kind: 'verbatim' | 'approved_summary' | 'editorial';
  sourceRefIds: string[];
  approved: boolean;
}
export interface LabelInstance {
  id: string;
  labelId: string;
  ownerId: string;
  role: 'title' | 'section' | 'task' | 'method' | 'condition' | 'readout' | 'caption' | 'legend';
  required: boolean;
}
export interface FigureContent {
  schemaVersion: '1.0';
  figureId: string;
  purpose: string;
  domain: string;
  studyStatus: StudyState;
  sources: SourceRef[];
  entities: ScientificEntity[];
  tasks: Array<{id: string; titleLabelId: string; state: StudyState; sourceRefIds: string[]}>;
  relations: ScientificRelation[];
  labels: ApprovedLabel[];
  labelInstances: LabelInstance[];
}
export interface TextSafeRegion {
  id: string;
  ownerId: string;
  normalizedBounds: readonly [number,number,number,number];
  labelInstanceIds: string[];
  minimumFontPt: number;
  maxLines: number;
  paddingPx: number;
  fontFamily: string;
  fitStatus: 'pending' | 'fits' | 'reflow_required';
}
export interface CompositionPlan {
  figureId: string;
  route: RenderRoute;
  layoutMasterId: string;
  grammar: { primary: string; modifiers: string[]; assetTreatments: string[] };
  styleId: string;
  canvas: { widthPx: number; heightPx: number; printWidthMm?: number };
  textRegions: TextSafeRegion[];
  relationEdges: Array<{ relationId: string; fromRegionId: string; toRegionId: string }>;
  assetRequests: Array<{ entityId: string; assetId?: string; required: boolean }>;
}
export interface SceneObject {
  id: string;
  type: 'shape' | 'text' | 'image' | 'connector' | 'group';
  normalizedBounds: readonly [number,number,number,number];
  zIndex: number;
  sourceContentIds: string[];
  labelInstanceId?: string;
  relationId?: string;
  assetId?: string;
}
export interface FigureScene {
  figureId: string;
  sourceContentHash: string;
  compositionHash: string;
  objects: SceneObject[];
}
export interface ImageCapabilityContract {
  generate: boolean;
  edit: boolean;
  imageReference: boolean;
  maskInput: boolean;
  layerDecomposition: boolean;
  transparentOutput: boolean;
  verifiedOperations: string[];   // verified means actual adapter contract test passed
}
