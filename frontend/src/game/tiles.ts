const HONOR_LABELS = ['동', '남', '서', '북', '백', '발', '중']
const RED_FIVE_IDS = new Set([16, 52, 88])

export type TileDisplay = {
  label: string
  suit: 'man' | 'pin' | 'sou' | 'honor'
  red: boolean
}

export function tileIdToDisplay(tileId: number): TileDisplay {
  if (!Number.isInteger(tileId) || tileId < 0 || tileId > 135) {
    throw new RangeError(`invalid RiichiEnv tile id: ${tileId}`)
  }

  const tileKind = Math.floor(tileId / 4)
  if (tileKind >= 27) {
    return {
      label: HONOR_LABELS[tileKind - 27],
      suit: 'honor',
      red: false,
    }
  }

  const suitIndex = Math.floor(tileKind / 9)
  const value = (tileKind % 9) + 1
  const suits = ['man', 'pin', 'sou'] as const
  const suffixes = ['만', '통', '삭']
  return {
    label: `${value}${suffixes[suitIndex]}`,
    suit: suits[suitIndex],
    red: RED_FIVE_IDS.has(tileId),
  }
}

export function seatWindLabel(seat: number, dealerSeat: number): string {
  return ['동', '남', '서', '북'][(seat - dealerSeat + 4) % 4]
}

export function roundWindLabel(roundWind: number): string {
  return ['동', '남', '서', '북'][roundWind] ?? `풍 ${roundWind}`
}
