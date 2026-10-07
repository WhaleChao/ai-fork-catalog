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

- `without workflow scope`／`workflows scope may be required`：到 [classic tokens](https://github.com/settings/tokens) 編輯 `FORK_PAT` 對應的專用 token。確認接受網頁連帶啟用的 `repo` 權限後，加上 `workflow` 並儲存。若重新產生金鑰，原值會失效，**還需將新值貼入 [Actions secret `FORK_PAT`](https://github.com/WhaleChao/ai-fork-catalog/settings/secrets/actions/FORK_PAT)**；只更新 token 頁面不會自動更新 secret。完成後手動執行 `refresh`，不會新增 fork，也不占每日 3 個名額。
- `合併衝突`：fork 有自己的修改且與上游衝突，需個別處理；自動化不會強制覆寫。
- HTTP 401：token 已失效或到期，需更新 `FORK_PAT`。

執行會先檢查 classic token 的權限。缺少 `workflow` 時仍可建立與整理 fork，但會略過整批同步，集中留下單一權限修正提示。真正的同步 API 失敗會讓 Actions 顯示失敗；已知合併衝突只列入報告。每次執行的 Summary 會區分 API 異常、合併衝突及略過同步。

目前 `llama-cpp-turboquant` 與 `project-golem` 的預設分支有上游合併衝突；自動化會持續記錄，需在各 fork 手動解決，並不會覆寫你的提交。

排程若長期未執行，檢查 Actions 是否因 GitHub 的[公開倉庫閒置規則](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)而停用，以及 `FORK_PAT` 是否已到期。
