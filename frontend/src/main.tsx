import React from 'react'
import ReactDOM from 'react-dom/client'
import { MahjongTable } from './game/MahjongTable'
import type { GameScreenState } from './game/types'
import './style.css'

function App() {
  const gameState: GameScreenState = { status: 'waiting' }

  return (
    <main className="shell">
      <header className="app-header">
        <p className="eyebrow">4-PLAYER RIICHI MAHJONG</p>
        <h1>No Riichi No Fuku</h1>
        <p>플레이어 1명과 CPU 3명이 진행하는 동풍전</p>
      </header>
      <MahjongTable state={gameState} onAction={() => undefined} />
    </main>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
