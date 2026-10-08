# 操作與授權

這個公開倉庫每天台北時間 10:17 搜尋 MAGI 相關技術，最多新增 3 個 fork，並嘗試同步 `WhaleChao` 的全部公開 fork。首次批次固定為 `data/seed.json` 的 30 個來源，只有手動執行 `bootstrap` 才會處理。

## 首次啟用

1. 在 GitHub 建立**有到期日**的專用 Personal Access Token (classic)。排程需要跨倉庫建立 fork、更新簡介與同步；上游若修改 `.github/workflows/`，同步還需要 `workflow`，只有 `public_repo` 會被 GitHub 以 HTTP 422 拒絕。**GitHub 目前的 classic token 網頁會在勾選 `workflow` 時，自動勾選並鎖定 `repo`；這包含私有倉庫存取，必須由帳戶擁有者確認後才啟用。** 程式只列舉與修改公開 fork，但 token 本身的權限仍較廣。若不接受此範圍，保留 `public_repo`，自動化會略過同步並回報缺少權限。管理倉庫自己的 `GITHUB_TOKEN` 不具備這些跨倉庫權限。[GitHub token 說明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) · [workflow scope 說明](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
2. 到此倉庫的 Settings → Secrets and variables → Actions，新增 repository secret `FORK_PAT`，貼入 token。不要把 token 寫入檔案、Issue、PR 或 workflow log。
3. 首次 30 個 fork 已於 2026-09-13 建立。到 Actions → MAGI Fork Catalog 選 `preview` 查看候選，再選 `daily` 驗證後續排程；`bootstrap` 仍可安全重跑，但不會重複建立同來源 fork。
4. 如有專案摘要或分類需要更正，編輯 `data/overrides.json`。現有的個人化 fork 簡介不會被覆寫。

## 模式

- `preview`：只讀取 GitHub，列出尚未 fork 的首批來源；不建立 fork、不同步、不寫入任何檔案。
- `bootstrap`：按 `data/seed.json` 處理首次 30 個來源，重跑時以來源 fork 網路去重；之後同步並重建目錄。
- `daily`：依主題、千星、授權、活躍度及用途條件搜尋，每日最多新增 3 個，然後同步並重建目錄。
- `refresh`：只同步現有 fork 並重建目錄。

同步使用 GitHub 的 `merge-upstream` API，不強制推送；衝突或 API 失敗會寫入 `data/report.json`。摘要沿用原專案語言，公開目錄不含私有 MAGI 倉庫的實作細節。AGPL／GPL 項目標為架構參考，真正整合程式碼前另行檢查授權。

## 排除同步錯誤

### 參考 fork 的 CI 與郵件

同步分支會觸發 fork 繼承的上游 Actions。原作者的 Secrets、發佈權限或 runner 在 fork 中往往不可用，可能造成大量失敗通知；這與 `merge-upstream` API 成功是兩件事。

`data/actions-policy.json` 明列需要停用繼承 Actions 的參考 fork。同步這些 fork 前，程式先停用倉庫 Actions 並再次讀取驗證；防護失敗時不更新該分支，原因會寫入報告與 Summary。程式不刪除 workflow 檔案或提交，因此仍可正常取得上游程式碼。

啟用 `disable_new_fork_actions` 後，此自動化之後新增的 fork 也納入相同防護；名稱存於 `data/state.json` 的 `reference_actions_forks`。既有 fork 只有明列者會受影響。`keep_actions` 可保留正在開發的 fork，預設保留 `codex-chatgpt-web`；目錄倉庫本身永遠排除。若要使用 CI，先加入 `keep_actions`，再至該 fork 的 Settings → Actions → General 重新啟用 Actions。

`preview` 只列出防護名單，仍不修改設定。停用 Actions 不會自動取消已排隊或執行中的工作；首次處理需另行取消，既有通知可能仍在陸續送達。帳戶通知保持原設定，自己開發專案的失敗通知不會被一併關閉。

- `without workflow scope`／`workflows scope may be required`：到 [classic tokens](https://github.com/settings/tokens) 編輯 `FORK_PAT` 對應的專用 token。確認接受網頁連帶啟用的 `repo` 權限後，加上 `workflow` 並儲存。若重新產生金鑰，原值會失效，**還需將新值貼入 [Actions secret `FORK_PAT`](https://github.com/WhaleChao/ai-fork-catalog/settings/secrets/actions/FORK_PAT)**；只更新 token 頁面不會自動更新 secret。完成後手動執行 `refresh`，不會新增 fork，也不占每日 3 個名額。
- `合併衝突`：fork 有自己的修改且與上游衝突，需個別處理；自動化不會強制覆寫。
- HTTP 401：token 已失效或到期，需更新 `FORK_PAT`。

執行會先檢查 classic token 的權限。缺少 `workflow` 時仍可建立與整理 fork，但會略過整批同步，集中留下單一權限修正提示。真正的同步 API 失敗會讓 Actions 顯示失敗；已知合併衝突只列入報告。每次執行的 Summary 會區分 API 異常、合併衝突及略過同步。

衝突名單以當次 `data/report.json` 與 Actions Summary 為準。若帳戶擁有者明確要求覆寫，先建立保留原提交的備份分支，再將 fork 的預設分支對齊直接上游的同名分支；日常自動化仍不會強制覆寫提交。

排程若長期未執行，檢查 Actions 是否因 GitHub 的[公開倉庫閒置規則](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)而停用，以及 `FORK_PAT` 是否已到期。
