export const DEFEAT_STAGE_LABELS = [
  '정상 · 일상복',
  '1단계 · 자켓/겉옷 벗음',
  '2단계 · 속옷만 착용',
  '3단계 · 알몸 · 최종 완료',
] as const

export function defeatStageLabel(stage: number): string {
  return DEFEAT_STAGE_LABELS[stage] ?? `알 수 없는 단계 (${stage})`
}
