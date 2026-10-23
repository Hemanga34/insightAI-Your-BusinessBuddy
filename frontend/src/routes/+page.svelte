<script lang="ts">
  import { onMount } from 'svelte';
  import { api, setToken, type Workspace, type SourceDocument } from '$lib/api';

  let workspace = $state<Workspace | null>(null);
  let documents = $state<SourceDocument[]>([]);
  let selected = $state<SourceDocument | null>(null);
  let mode = $state<'login' | 'register'>('register');
  let email = $state('');
  let password = $state('');
  let businessName = $state('');
  let industry = $state('');
  let busy = $state(false);
  let uploading = $state(false);
  let error = $state('');
  let notice = $state('');
  let session = 0;
  const statuses: Record<string, string> = {
    queued: 'Queued', processing: 'Extracting', extracted: 'Ready to inspect',
    needs_attention: 'Needs attention', failed: 'Processing failed'
  };

  async function refresh() {
    const current = session;
    const result = await api<SourceDocument[]>('/documents');
    if (current === session && workspace) documents = result;
  }

  onMount(() => {
    const timer = setInterval(() => {
      if (workspace && documents.some(d => ['queued', 'processing'].includes(d.status))) {
        refresh().catch(e => { error = e.message; });
      }
    }, 3000);
    return () => clearInterval(timer);
  });

  async function authenticate(event: SubmitEvent) {
    event.preventDefault();
    busy = true; error = '';
    try {
      const payload = mode === 'register'
        ? { email, password, business_name: businessName, industry } : { email, password };
      const result = await api<{ access_token: string }>(`/auth/${mode}`, {
        method: 'POST', body: JSON.stringify(payload)
      });
      setToken(result.access_token);
      workspace = await api<Workspace>('/workspace');
      password = '';
      await refresh();
    } catch (e) { error = e instanceof Error ? e.message : 'Could not sign in'; }
    finally { busy = false; }
  }

  async function upload(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    uploading = true; error = ''; notice = '';
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('Choose a file smaller than 20 MB.');
      const form = new FormData(); form.append('file', file);
      await api('/documents', { method: 'POST', body: form });
      await refresh();
      notice = 'Document received. Inspect the extracted text before using its figures.';
    } catch (e) { error = e instanceof Error ? e.message : 'Upload failed'; }
    finally { uploading = false; input.value = ''; }
  }

  async function inspect(document: SourceDocument) {
    error = '';
    const current = session;
    try {
      const detail = await api<SourceDocument>(`/documents/${document.id}`);
      if (current === session && workspace) selected = detail;
    }
    catch (e) { error = e instanceof Error ? e.message : 'Could not open document'; }
  }

  async function retry(document: SourceDocument) {
    error = '';
    try {
      await api(`/documents/${document.id}/retry`, { method: 'POST' });
      selected = null;
      await refresh();
    } catch (e) { error = e instanceof Error ? e.message : 'Could not retry'; }
  }

  function signOut() {
    session += 1; setToken(''); workspace = null; documents = []; selected = null;
    error = ''; notice = ''; password = '';
  }
</script>

<svelte:head><title>InsightAI · Your business, understood</title>
  <meta name="description" content="A financial workspace for Indian business owners and founders." />
</svelte:head>

<div class="shell">
  <aside>
    <a class="brand" href="/">◈ <span>InsightAI<span class="brand-dot">.</span></span></a>
    <div class="workspace-label">BUSINESS WORKSPACE</div>
    <div class="nav-current">▤ <span>Documents</span></div>
    <div class="nav-future">◷ <span>Financial overview</span><small>Next</small></div>
    <div class="nav-future">↗ <span>Market intelligence</span><small>Next</small></div>
    <div class="nav-future">▦ <span>Meetings</span><small>Next</small></div>
    <div class="aside-footer"><span class="india-dot"></span> Built for Indian businesses<br /><span>INR · April–March · IST</span></div>
  </aside>
  <main>
    <header><span>YOUR FINANCIAL WORKSPACE</span><div class="header-right"><span class="release">EARLY BUILD</span>{#if workspace}<button class="text-button" onclick={signOut}>Sign out</button>{/if}</div></header>
    {#if error}<div class="alert error" role="alert">{error}</div>{/if}
    {#if notice}<div class="alert" role="status">{notice}</div>{/if}
    {#if !workspace}
      <div class="welcome-grid">
        <section class="intro"><div class="eyebrow">CLARITY STARTS HERE</div>
          <h1>Your business.<br />A clearer picture.</h1>
          <p>Bring your financial documents into one workspace. The first step toward understanding where your money goes—and what comes next.</p>
          <div class="intro-line"></div>
          <div class="feature"><span>01</span><div><strong>Bring your documents</strong><p>Bank statements, invoices, spreadsheets and more.</p></div></div>
          <div class="feature"><span>02</span><div><strong>Inspect the source</strong><p>See extracted text with page, sheet and row references.</p></div></div>
          <div class="feature"><span>03</span><div><strong>Build on verified information</strong><p>Financial insights and actions are the next milestone.</p></div></div>
        </section>
        <section class="auth-card"><div class="eyebrow">LET’S GET STARTED</div><h2>{mode === 'register' ? 'Create your workspace' : 'Welcome back'}</h2>
          <p class="muted">{mode === 'register' ? 'A dedicated space for your business documents.' : 'Sign in to your business workspace.'}</p>
          <form onsubmit={authenticate}>
            {#if mode === 'register'}<label>Business name<input bind:value={businessName} required minlength="2" maxlength="120" placeholder="e.g. Northstar Foods" autocomplete="organization" /></label>
              <label>Industry <span class="optional">optional</span><input bind:value={industry} maxlength="120" placeholder="e.g. Food & beverage" /></label>{/if}
            <label>Email<input type="email" bind:value={email} required autocomplete="email" placeholder="you@business.in" /></label>
            <label>Password<input type="password" bind:value={password} required minlength="12" maxlength="128" autocomplete={mode === 'register' ? 'new-password' : 'current-password'} placeholder="At least 12 characters" /></label>
            <button class="primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'register' ? 'Create workspace →' : 'Sign in →'}</button>
          </form>
          <button class="switch" disabled={busy} onclick={() => { mode = mode === 'register' ? 'login' : 'register'; error = ''; }}>{mode === 'register' ? 'Already have a workspace? Sign in' : 'New here? Create a workspace'}</button>
          <p class="session-note">Your sign-in lasts for this page session. Refreshing the page requires signing in again.</p>
        </section>
      </div>
    {:else}
      <section class="page-heading"><div><div class="eyebrow">{workspace.name} / DOCUMENTS</div><h1>Your documents, together.</h1><p>Start with the source. Inspect your data before turning it into decisions.</p></div><span class="currency">₹ INR</span></section>
      <div class="stats"><div><span>DOCUMENTS</span><strong>{documents.length}</strong><small>Most recent 100 uploads</small></div><div><span>READY TO INSPECT</span><strong>{documents.filter(d => d.status === 'extracted').length}</strong><small>Text extracted, figures unverified</small></div><div><span>FINANCIAL INSIGHTS</span><strong class="coming">Coming next</strong><small>Built from reviewed records</small></div></div>
      <section class="upload-card"><div class="upload-icon">↑</div><h2>Bring your financial documents</h2><p>Upload one file at a time. Original documents stay in your business workspace.</p><label class="upload-button">{uploading ? 'Uploading…' : 'Choose a document'}<input type="file" accept=".pdf,.xlsx,.xls,.csv,.docx,.jpg,.jpeg,.png" onchange={upload} disabled={uploading} /></label><small>PDF, Excel, CSV, Word and images · Up to 20 MB</small><p class="ocr-note">Text PDFs and Office files support extraction now. Scans and images are accepted and flagged for OCR, which is not enabled yet.</p></section>
      <section class="document-section"><div class="section-heading"><h2>Document library</h2><button class="text-button" onclick={() => refresh().catch(e => { error = e.message; })}>Refresh ↻</button></div>
        {#if documents.length === 0}<div class="empty"><span>▤</span><h3>A clean slate for clearer finances.</h3><p>Your uploaded documents will appear here.</p></div>
        {:else}<div class="table-wrap"><table><thead><tr><th>DOCUMENT</th><th>SIZE</th><th>STATUS</th><th><span class="sr-only">Actions</span></th></tr></thead><tbody>{#each documents as document}<tr><td><strong>{document.filename}</strong><small>{document.extension.slice(1).toUpperCase()}</small></td><td>{(document.size_bytes / 1024).toFixed(1)} KB</td><td><span class:attention={['failed', 'needs_attention'].includes(document.status)} class="status">{statuses[document.status] || document.status}</span></td><td><button class="text-button" onclick={() => inspect(document)}>Inspect →</button></td></tr>{/each}</tbody></table></div>{/if}
      </section>
      {#if selected}<section class="preview"><div class="section-heading"><h2>{selected.filename}</h2><button class="text-button" onclick={() => selected = null}>Close ×</button></div><p class="muted">Extracted text · Unverified · Not included in financial totals</p>{#if selected.error}<div class="alert error">{selected.error}</div>{/if}{#if ['failed', 'needs_attention'].includes(selected.status)}<button class="secondary" onclick={() => retry(selected!)}>Retry processing</button>{/if}{#if selected.extraction}{#each selected.extraction.blocks as block}<div class="source-block"><small>{Object.entries(block.location).map(([key, value]) => `${key} ${value}`).join(' · ')}</small><pre>{block.text}</pre></div>{/each}{:else}<p>No extracted text is available yet. Refresh the library and inspect again after processing.</p>{/if}</section>{/if}
    {/if}
    <footer>InsightAI <span>Financial clarity, one document at a time.</span></footer>
  </main>
</div>

<style>
  :global(*){box-sizing:border-box} :global(body){margin:0;background:#f7f8f5;color:#21392f;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px} :global(button),:global(input){font:inherit} :global(button){cursor:pointer} :global(button:disabled){cursor:wait;opacity:.6} :global(button:focus-visible),:global(a:focus-visible),:global(input:focus-visible){outline:3px solid #a7bb74;outline-offset:3px}
  .shell{display:flex;min-height:100vh} aside{width:248px;background:#143d32;color:#fff;padding:38px 23px;position:fixed;inset:0 auto 0 0;display:flex;flex-direction:column}.brand{color:#fff;text-decoration:none;display:flex;gap:10px;align-items:center;font-size:26px;font-weight:650;letter-spacing:-1px}.brand-dot{color:#c8dc94}.workspace-label{font-size:10px;letter-spacing:1.8px;color:#9bb7a9;margin:62px 12px 20px}.nav-current,.nav-future{display:flex;gap:12px;align-items:center;padding:14px 12px;margin:3px 0;border-radius:7px;font-size:13px}.nav-current{background:#2e5346;color:#e1edc5}.nav-future{color:#9eb6aa}.nav-future small{margin-left:auto;font-size:9px;border:1px solid #4a685b;padding:2px 4px;border-radius:3px}.aside-footer{margin-top:auto;font-size:11px;color:#dce8df;line-height:2}.aside-footer>span:last-child{padding-left:14px;color:#9bb7a9}.india-dot{display:inline-block;width:6px;height:6px;border-radius:100%;background:#c8dc94;margin-right:7px}
  main{margin-left:248px;width:calc(100% - 248px);padding:0 48px}header{height:92px;border-bottom:1px solid #dfe5dd;display:flex;align-items:center;justify-content:space-between;font-size:10px;letter-spacing:1.8px;color:#708073}.header-right{display:flex;gap:20px;align-items:center}.release{border:1px solid #d6ded0;border-radius:4px;padding:6px 9px;font-size:9px;color:#53684a}.welcome-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:8%;padding:66px 0 72px;align-items:start}.eyebrow{font-size:10px;letter-spacing:2px;color:#728463;font-weight:650;text-transform:uppercase}h1{font-weight:500;font-size:clamp(32px,3.6vw,54px);line-height:1.12;letter-spacing:-2px;margin:20px 0}h2{font-size:23px;font-weight:550;letter-spacing:-.6px;margin:15px 0}p{line-height:1.75;color:#6c7b70}.intro>p{font-size:15px;max-width:420px}.intro-line{width:50px;height:2px;background:#b7cb88;margin:32px 0}.feature{display:flex;gap:18px;margin:24px 0}.feature>span{font-size:11px;color:#8c9b78;padding-top:3px}.feature strong{font-size:13px;font-weight:550}.feature p{font-size:12px;margin:6px 0}.auth-card{background:white;border:1px solid #dfe5da;border-radius:12px;padding:32px;box-shadow:0 10px 40px #183b2b05}.muted{font-size:12px;color:#7b877d}.auth-card form{margin-top:25px}label{display:block;font-size:12px;font-weight:550;margin-bottom:17px}input{display:block;width:100%;margin-top:8px;padding:12px 13px;border:1px solid #d9e1d6;border-radius:6px;background:#fcfdfb;color:#233b30;min-width:0}input::placeholder{color:#9ca69a;font-size:12px}.optional{font-size:10px;font-weight:400;color:#909d8b;margin-left:4px}.primary{width:100%;padding:14px;background:#204c39;border:0;border-radius:6px;color:#fff;font-weight:550;margin-top:4px}.switch{background:none;border:0;color:#557344;font-size:11px;width:100%;margin:22px 0 0}.session-note{font-size:10px;border-top:1px solid #edf0e9;padding-top:17px;margin-bottom:0}.text-button{border:0;background:none;color:#49704b;font-size:12px;padding:8px}.alert{background:#eaf0dc;padding:13px 18px;border-radius:6px;margin-top:18px;line-height:1.6}.error{background:#fbece5;color:#914d34}.page-heading{display:flex;justify-content:space-between;align-items:center;margin:45px 0 30px}.page-heading h1{font-size:37px;margin:14px 0}.page-heading p{margin:0}.currency{border:1px solid #d9e1d1;padding:7px 10px;border-radius:5px;font-size:11px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:28px 0}.stats>div{background:white;border:1px solid #dfe5da;padding:23px;border-radius:8px;display:flex;flex-direction:column;gap:10px}.stats span{font-size:9px;letter-spacing:1.5px;color:#7a8872}.stats strong{font-weight:500;font-size:30px}.stats small{color:#7c8976;font-size:10px}.stats .coming{font-size:20px;line-height:36px;color:#8b997f}.upload-card{text-align:center;border:1px dashed #b9c8aa;background:#f0f4e9;border-radius:10px;padding:29px}.upload-icon{font-size:28px;color:#5c7844}.upload-card h2{font-size:20px;margin:8px 0}.upload-card p{font-size:12px;margin:7px 0}.upload-button{position:relative;display:inline-block;overflow:hidden;background:#24503c;color:white;padding:12px 20px;border-radius:6px;margin:15px 0;cursor:pointer}.upload-button input{position:absolute;inset:0;opacity:0;margin:0;cursor:pointer;height:100%}.upload-card>small{display:block;font-size:10px;color:#75856b}.upload-card .ocr-note{font-size:10px;max-width:540px;margin:15px auto 0}.document-section{margin-top:30px}.section-heading{display:flex;justify-content:space-between;align-items:center;gap:12px}.section-heading h2{font-size:19px;overflow-wrap:anywhere}.empty{background:white;border:1px solid #e0e6dc;border-radius:8px;text-align:center;padding:40px}.empty>span{font-size:28px;color:#a3b392}.empty h3{font-size:14px;font-weight:500}.empty p{font-size:12px}.table-wrap{overflow:auto;border:1px solid #e0e6dc;border-radius:8px;background:#fff}table{border-collapse:collapse;width:100%;text-align:left;font-size:12px}th{font-size:9px;letter-spacing:1px;color:#85917c;background:#f0f3eb;padding:15px}td{padding:15px;border-top:1px solid #edf0e8}td strong{font-weight:500;overflow-wrap:anywhere}td small{display:block;font-size:9px;color:#9aa58f;margin-top:5px}.status{display:inline-block;border-radius:4px;background:#edf2e4;padding:5px 8px;font-size:10px;white-space:nowrap}.status.attention{background:#fcf0dc;color:#9b6f31}.preview{margin-top:24px;padding:24px;border:1px solid #dfe5da;background:#fff;border-radius:8px}.source-block{border-top:1px solid #e6ebdf;margin-top:15px;padding-top:15px}.source-block small{color:#70895d;font-size:10px;text-transform:uppercase}.source-block pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#475441;line-height:1.6}.secondary{padding:10px 15px;background:#eef2e8;border:1px solid #d2ddc7;border-radius:5px;color:#3d5a30}footer{border-top:1px solid #dfe5da;padding:24px 0;margin-top:32px;font-size:11px;color:#607558;display:flex;justify-content:space-between}footer span{color:#96a08e}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
  @media(min-width:1500px){main{padding:0 7%}.welcome-grid{gap:10%;padding-top:90px}}@media(max-width:1050px){aside{width:200px;padding:30px 15px}main{margin-left:200px;width:calc(100% - 200px);padding:0 28px}.welcome-grid{gap:30px}.auth-card{padding:25px}.stats{gap:10px}.nav-future{font-size:11px;gap:8px}}@media(max-width:800px){aside{position:static;width:100%;padding:20px;display:block}.shell{display:block}.brand{font-size:24px}.workspace-label,.nav-current,.nav-future,.aside-footer{display:none}main{margin-left:0;width:100%;padding:0 22px}header{height:64px}.welcome-grid{grid-template-columns:1fr;padding:35px 0;gap:25px}.intro h1{font-size:42px}.intro-line,.feature{display:none}.auth-card{max-width:500px;width:100%;margin:auto}.page-heading h1{font-size:30px}.stats{grid-template-columns:1fr}.stats>div{padding:16px}.page-heading{margin-top:30px}.stats strong{font-size:24px}footer span{max-width:170px;text-align:right}}
</style>
