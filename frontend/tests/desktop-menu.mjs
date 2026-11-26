export async function enterDesktopGame(page) {
  await page.getByRole('button', {name:'메인 메뉴로', exact:true}).click()
  const menu = page.getByRole('navigation', {name:'메인 메뉴', exact:true})
  const start = menu.getByRole('button', {name:'새로 시작'})
  await page.waitForFunction(() => document.querySelector('.front-menu .primary-button:enabled'))
  const resume = menu.getByRole('button', {name:'이어하기'})
  await (await resume.isEnabled() ? resume : start).click()
}
