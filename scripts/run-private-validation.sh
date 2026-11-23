#!/usr/bin/env bash
set -euo pipefail
ROOT="${SA_SOURCE_DIR:-private-source}"
cd "$ROOT"
TASK="${SA_TASK:?SA_TASK is required}"

case "$TASK" in
  catbox-diagnostic)
    node tests/catbox-transport-diagnostic.mjs
    ;;
  catbox-source-smoke)
    node --test tests/live-catbox.test.mjs
    ;;
  catbox-review-download)
    node --check engine/chatgpt-review-adapter.js
    node --test tests/chatgpt-review-adapter.test.cjs
    ;;
  cherry-mirror-audit)
    node tests/cherry-mirror-recovery.mjs
    ;;
  cloud-smoke)
    node --input-type=module <<'NODE'
    import fs from 'node:fs';
    const current=fs.readFileSync('index.html','utf8');
    const version=/class="version">([^<]+)/.exec(current)?.[1];
    if(!version)throw Error('Website version marker is missing');
    let ready=false;
    for(let attempt=1;attempt<=30;attempt++){
      try{
        const url='https://spineanimator.github.io/?release='+process.env.GITHUB_SHA+'-'+attempt;
        const response=await fetch(url,{headers:{'cache-control':'no-cache'},signal:AbortSignal.timeout(10000)});
        if(response.ok&&(await response.text()).includes('class="version">'+version+'</span>')){
          console.log('Production Pages published '+version+' on attempt '+attempt);
          ready=true;break;
        }
      }catch(error){console.log('Pages pending: '+String(error.message).slice(0,150));}
      await new Promise(resolve=>setTimeout(resolve,5000));
    }
    if(!ready)throw Error('Production Pages did not publish '+version+' within readiness window');
NODE
    node --test tests/live-cloud.test.mjs
    ;;
  drive-source-smoke)
    node --test tests/live-drive-source.test.mjs
    ;;
  mcp-real-psd)
    node tools/download_verified_catbox.mjs .verified-source
    python -m pip install --disable-pip-version-check 'psd-tools>=1.10,<2' 'Pillow>=10.3,<14' 'scipy>=1.10,<2'
    python tools/extract_psd_rasters.py .verified-source/clgb71.psd .test-output/mcp-real/raster
    node --test tests/js-psd-scene.test.mjs
    node tools/build_psd_scene.mjs .test-output/mcp-real/raster .test-output/mcp-real zombie_pistol
    node --test tests/live-mcp-real-psd.mjs
    ;;
  mcp-source-smoke)
    node tests/live-mcp-source.mjs
    ;;
  mcp-zip-live)
    node --test tests/live-mcp-zip.mjs
    ;;
  nf4g80-probe)
    node --input-type=module <<'NODE'
    import { createHash } from 'node:crypto';
    const original='https://files.catbox.moe/nf4g80.psd';
    const checks=[
      ['files-catbox',original],
      ['litter-catbox','https://litter.catbox.moe/nf4g80.psd'],
      ['cloudflare-cache','https://spine-psd-cache.spine-animator-f8692224.workers.dev/api/psd-source?url='+encodeURIComponent(original)],
      ['cloudflare-generator','https://spine-generator.spine-animator-f8692224.workers.dev/api/psd-source?url='+encodeURIComponent(original)]
    ];
    for(const [name,url] of checks){
      const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),15500);
      try{
        const r=await fetch(url,{headers:{accept:'application/octet-stream',origin:'https://spineanimator.github.io'},redirect:'manual',signal:ctl.signal});
        if(!r.ok){const b=await r.text();console.log('NF4G80_PROBE',JSON.stringify({name,status:r.status,error:b.slice(0,230)}));continue;}
        const digest=createHash('sha256'),head=[],reader=r.body?.getReader();
        if(!reader)throw Error('Missing body');
        let count=0;
        for(;;){const {done,value}=await reader.read();if(done)break;
          if(count<26)head.push(...value.slice(0,26-count));
          count+=value.length;if(count>180*1024*1024)throw Error('Too large');
          digest.update(value);
        }
        const magic=Buffer.from(head).subarray(0,6).toString('hex');
        const sha=digest.digest('hex');
        console.log('NF4G80_PROBE',JSON.stringify({name,status:r.status,valid:magic==='384250530001',bytes:count,sha256:sha,
          matchesHistoricalCherry:count===40062699&&sha==='b5f50a5dc500ee2c45d1c817213995ab092a33b754febc903aa5e861b20757d4'}));
      }catch(error){console.log('NF4G80_PROBE',JSON.stringify({name,error:String(error.message||error).slice(0,200)}));}
      finally{clearTimeout(timer);}
    }
NODE
    ;;
  pose-director)
    node --check engine/pose-director.js
    node --check engine/artistic-score.js
    node --check engine/scene.js
    node --check engine/scene-export.js
    node --check engine/remote-planner.js
    node --test tests/pose-director.test.cjs tests/artistic-score.test.cjs tests/remote-planner.test.cjs
    npm run build:cloud-generator
    ;;
  psd-1000)
    mkdir -p reports
    BENCHMARK_TOTAL=1000 BENCHMARK_MIN_SUCCESS=990 BENCHMARK_CONCURRENCY=4 BENCHMARK_REPORT=reports/psd-1000.json node tests/psd-1000-live.mjs
    ;;
  psd-cache-unit)
    node --test tests/psd-cache-autoheal.test.cjs
    ;;
  psd-cloud-smoke)
    python -m pip install --disable-pip-version-check 'psd-tools>=1.10,<2' 'Pillow>=10.3,<14' 'scipy>=1.10,<2'
    python tools/extract_psd_rasters.py tests/fixtures/etalons/cherry/source.psd .test-output/psd-cloud/raster
    node tools/build_psd_scene.mjs .test-output/psd-cloud/raster .test-output/psd-cloud generic
    node tools/post_cloud_fixture.mjs .test-output/psd-cloud/cloud-request.json .test-output/psd-cloud/psd-cloud-spine.zip
    node tools/verify_psd_cloud_bundle.mjs .test-output/psd-cloud/raster .test-output/psd-cloud
    node --test tests/psd-cloud-runtime.test.mjs
    ;;
  psd-route-audit)
    node tests/psd-route-audit-live.mjs
    ;;
  recover-zombie-source)
    node --test tests/download-verified-catbox.test.mjs
    node tools/download_verified_catbox.mjs .verified-source
    ;;
  runtime-contact)
    node --test tests/runtime-contact-evidence.test.mjs
    ;;
  storage-diagnostic)
    node tests/storage-source-diagnostic.mjs
    ;;
  site-command)
    node --test tests/command.test.cjs tests/remote-planner.test.cjs tests/cloud-generator.test.cjs
    node --test --test-name-pattern='@2Spine' tests/app.test.cjs
    ;;
  rust-core)
    cargo test --manifest-path rust/spine-core/Cargo.toml
    cargo build --release --target wasm32-unknown-unknown --manifest-path rust/spine-core/Cargo.toml
    cp rust/spine-core/target/wasm32-unknown-unknown/release/spine_core.wasm engine/spine_core.wasm
    REQUIRE_RUST_MESH=1 node --test tests/rust-core.test.cjs
    ;;
  zombie-psd)
    python -m pip install --disable-pip-version-check 'psd-tools>=1.10,<2' 'Pillow>=10.3,<14' 'scipy>=1.10,<2'
    python tools/verify_zombie_psd.py
    ;;
  volume360)
    python -m pip install --disable-pip-version-check 'psd-tools>=1.9,<2' 'Pillow>=10' 'scipy>=1.10,<2'
    python tools/passive_psd_rgba_for_360.py tests/fixtures/etalons/cherry/source.psd .test-output/volume360-input
    node tools/verify_real_psd_volume360.mjs .test-output/volume360-input .test-output/volume360-result
    unzip -t .test-output/volume360-result/real-psd-volume360-spine-4.3.26.zip
    node tools/assert-continuous-spine-zip.cjs .test-output/volume360-result/real-psd-volume360-spine-4.3.26.zip
    ;;
  full-node-tests)
    npm test
    node scripts/verify-art-evidence.cjs quality/reviews/cherry-art-head-unapproved.json "$GITHUB_SHA" --require-blocked
    node --test tests/js-ik-pack.test.mjs tests/js-psd-scene.test.mjs
    ;;
  asset-transport-unit)
    node --test tests/sa-agent-resize-bridge.test.cjs tests/sa-browser-adapter-exports.test.cjs tests/sa-production-pipeline.test.cjs tests/sa-reference-library-adapter.test.cjs tests/sa-production-adapters.test.cjs tests/archive-handler.test.cjs tests/asset-upload-client.test.cjs tests/asset-transport.test.cjs tests/chatgpt-review-adapter.test.cjs tests/model-gateway.test.cjs tests/sa-agent-runtime.test.cjs tests/sa-agent.test.cjs tests/sa-browser-runtime.test.cjs tests/sa-edge-contract.test.cjs tests/sa-edge-runtime.test.cjs tests/scene-ir-animation-planner.test.cjs
    npm run bench:sa-vision
    ;;
  browser-smoke)
    npm install --no-save --ignore-scripts playwright-core@1.58.2
    node --input-type=module <<'NODE'
    import { chromium } from 'playwright-core';
    import { existsSync } from 'node:fs';
    const chrome=['/usr/bin/google-chrome','/usr/bin/chromium','/opt/google/chrome/chrome'].find(existsSync);
    if(!chrome)throw Error('Headless Chrome is not available on runner');
    const browser=await chromium.launch({executablePath:chrome,args:['--no-sandbox'],headless:true});
    try{
      const page=await browser.newPage({viewport:{width:1280,height:900}});
      const messages=[];
      page.on('pageerror',e=>messages.push('pageerror '+String(e.message).slice(0,200)));
      page.on('response',r=>{if(/api\/plan|api\/build|bundle\.js/.test(r.url()))messages.push('HTTP '+r.status()+' '+r.url().split('?')[0]);});
      await page.goto('https://spineanimator.github.io/?qa='+Date.now(),{waitUntil:'networkidle',timeout:45000});
      await page.waitForFunction(()=>Boolean(window.agPsd?.readPsd),null,{timeout:20000});
      console.log('BROWSER_PSD_PARSER_READY',await page.evaluate(()=>Boolean(window.agPsd?.readPsd)));
      console.log('BROWSER_VERSION',await page.locator('.version').textContent());
      await page.locator('#source-file').setInputFiles('tests/fixtures/etalons/cherry/source.psd');
      await page.locator('#prompt').fill('Animate the cherry with a small bounce and return to the source pose');
      await page.locator('#generate').click();
      await page.waitForFunction(()=>/ZIP ready|Generation failed/.test(document.querySelector('#status')?.textContent||''),null,{timeout:60000});
      const result=await page.locator('#status').textContent();
      console.log('BROWSER_GENERATION_STATUS',result.slice(0,900));
      console.log('BROWSER_NETWORK_EVENTS',JSON.stringify(messages.slice(-20)));
      const ready=await page.locator('#download').evaluate(el=>!el.hidden&&!!el.href);
      console.log('BROWSER_DOWNLOAD_READY',ready);
      if(!ready)throw Error('Website failed to produce ZIP: '+result.slice(0,300));
    }finally{await browser.close()}
NODE
    ;;
  zombie-spine-e2e)
    python -m pip install --disable-pip-version-check 'psd-tools>=1.10,<2' 'Pillow>=10.3,<14' 'scipy>=1.10,<2'
    python -m unittest discover -s tests -p 'test_verify_zombie_psd.py'
    PSD_LAYER_MANIFEST=.test-output/zombie/original-layers.json python tools/verify_zombie_psd.py
    python tools/extract_psd_rasters.py /tmp/zombie-pistol.psd .test-output/zombie/cloud-raster
    node tools/build_psd_scene.mjs .test-output/zombie/cloud-raster .test-output/zombie zombie_pistol
    node tools/post_cloud_fixture.mjs .test-output/zombie/cloud-request.json .test-output/zombie/psd-cloud-spine.zip
    node tools/verify_psd_cloud_bundle.mjs .test-output/zombie/cloud-raster .test-output/zombie
    node --test tests/pose-director.test.cjs tests/artistic-score.test.cjs tests/remote-planner.test.cjs
    node --test tests/js-ik-pack.test.mjs tests/js-psd-scene.test.mjs
    node --test tests/runtime-contact-evidence.test.mjs
    node tools/verify_clgb71_rig.mjs .test-output/zombie/original-layers.json .test-output/zombie/rig-runtime-report.json .test-output/zombie/verified-ik-skeleton.json
    PSD_LAYER_MANIFEST=.test-output/zombie/original-layers.json node --test tests/real-clgb71-rig.test.cjs
    python tools/extract_clgb71_layers.py /tmp/zombie-pistol.psd .test-output/zombie/original-layers.json .test-output/zombie/rig-package
    node tools/package_clgb71_ik.mjs .test-output/zombie/original-layers.json .test-output/zombie/verified-ik-skeleton.json .test-output/zombie/rig-package .test-output/zombie/original-ik-spine-4.3.26.zip .test-output/zombie/ik-package-report.json
    node tools/export_spine_contact_poses.mjs --bundle .test-output/zombie/original-ik-spine-4.3.26.zip --out .test-output/zombie/runtime-contact-poses.json
    python -m unittest discover -s tests -p 'test_guard_spine_contacts.py'
    python tools/guard_spine_contacts.py --bundle .test-output/zombie/original-ik-spine-4.3.26.zip --report .test-output/zombie/attachment-contact-report.json
    python tools/verify_clgb71_fidelity.py /tmp/zombie-pistol.psd .test-output/zombie/original-ik-spine-4.3.26.zip .test-output/zombie/visual-evidence
    python tools/audit_spine43_candidate.py /tmp/zombie-pistol.psd .test-output/zombie/original-ik-spine-4.3.26.zip .test-output/zombie/spine43-editor-candidate-audit.json
    node tools/verify_clgb71_ik_package.mjs .test-output/zombie/rig-package
    PSD_CLOUD_SMOKE_DIR=.test-output/zombie SPINE_EXPECTED_CLIP=pistol_recoil node --test tests/psd-cloud-runtime.test.mjs
    ;;
  clgb71-ik-build)
    python -m pip install --disable-pip-version-check 'psd-tools[composite]>=1.10,<2' 'Pillow>=10.3,<14' 'numpy>=1.26,<3' 'scipy>=1.10,<2'
    python -m unittest discover -s tests -p 'test_psd_style_evidence.py'
    python -m unittest discover -s tests -p 'test_reconstruct_psd_rgb_appearance.py'
    PSD_FORCE_VERIFIED_CACHE=1 python tools/verify_zombie_psd.py
    python tools/verify_zombie_psd.py
    node --test tests/js-ik-pack.test.mjs
    node --test tests/real-clgb71-rig.test.cjs
    node --test tests/runtime-contact-evidence.test.mjs
    PSD_LAYER_MANIFEST=.test-output/clgb71-ik/original-layers.json node tools/verify_clgb71_rig.mjs .test-output/clgb71-ik/original-layers.json .test-output/clgb71-ik/rig-runtime-report.json .test-output/clgb71-ik/skeleton.json
    python tools/extract_clgb71_layers.py /tmp/zombie-pistol.psd .test-output/clgb71-ik/original-layers.json .test-output/clgb71-ik/package
    node tools/package_clgb71_ik.mjs .test-output/clgb71-ik/original-layers.json .test-output/clgb71-ik/skeleton.json .test-output/clgb71-ik/package .test-output/clgb71-ik/original-ik-spine-4.3.26.zip .test-output/clgb71-ik/ik-package-report.json
    node tools/export_spine_contact_poses.mjs --bundle .test-output/clgb71-ik/original-ik-spine-4.3.26.zip --out .test-output/clgb71-ik/runtime-contact-poses.json
    node tools/verify_clgb71_ik_package.mjs .test-output/clgb71-ik/package
    python tools/verify_clgb71_fidelity.py /tmp/zombie-pistol.psd .test-output/clgb71-ik/original-ik-spine-4.3.26.zip .test-output/clgb71-ik/psd-effect-evidence
    python tools/reconstruct_psd_rgb_appearance.py /tmp/zombie-pistol.psd .test-output/clgb71-ik/package/images .test-output/clgb71-ik/psd-rgb-candidate
    ;;
  *)
    echo "::error::Unknown SA validation task: $TASK"
    exit 2
    ;;
esac
