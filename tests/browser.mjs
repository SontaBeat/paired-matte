import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
const errors = [];
page.on('pageerror', err => errors.push(err.message));
try {
  await page.goto(pathToFileURL(path.join(root, 'cutout-tool.html')).href);
  const basic = await page.evaluate(() => {
    function fixture(w, h, pixel) { const c = document.createElement('canvas'); c.width=w; c.height=h; const x=c.getContext('2d'); x.fillStyle=pixel; x.fillRect(0,0,w,h); return c; }
    state.colorBitmap=fixture(8,8,'rgb(200,100,50)'); state.maskBitmap=fixture(8,8,'white'); processImages();
    const opaque = [...state.output.data.slice(0,4)];
    state.maskBitmap=fixture(8,8,'black'); processImages(); const empty=[...state.output.data.slice(0,4)];
    state.maskBitmap=fixture(8,8,'rgb(128,128,128)'); processImages(); const half=state.output.data[3];
    state.maskBitmap=fixture(4,4,'white'); processImages(); const blocked=!state.outputReady && els.downloadBtn.disabled;
    els.resizeMask.checked=true; processImages(); const resized=state.outputReady;
    return {opaque,empty,half,blocked,resized};
  });
  assert.deepEqual(basic.opaque,[200,100,50,255]);
  assert.deepEqual(basic.empty,[0,0,0,0]);
  assert.equal(basic.half,128); assert(basic.blocked && basic.resized);
  // Reload to use genuine ImageBitmaps in the public file-upload path.
  await page.reload();
  const ids = ['veil-warrior','silver-swordsman','magic-duo'];
  for (const id of ids) {
    const dir=path.join(root,'examples',id);
    await page.setInputFiles('#colorInput',path.join(dir,'solid.png'));
    await page.setInputFiles('#maskInput',path.join(dir,'alpha.png'));
    await page.waitForFunction(() => state.outputReady);
    await page.selectOption('#preset',id==='magic-duo'?'general':'cloth');
    await page.waitForTimeout(200);
    const dims = await page.evaluate(() => ({width:state.output.width,height:state.output.height}));
    const manifest = JSON.parse(await readFile(path.join(dir,'manifest.json'),'utf8'));
    assert.deepEqual(dims,manifest.size);
    await page.selectOption('#previewMode','overlay');
    const downloadPromise=page.waitForEvent('download');
    await page.click('#downloadBtn');
    const download=await downloadPromise;
    const dest=process.env.BUILD_EXAMPLES ? path.join(dir,'cutout.png') : path.join(root,'test-results',`${id}.png`);
    await mkdir(path.dirname(dest),{recursive:true});
    await download.saveAs(dest);
    // Export must remain RGBA result even while an overlay is visible.
    const resultAlpha=await page.evaluate(() => state.output.data[3]);
    assert.equal(resultAlpha,0);
    if(process.env.BUILD_EXAMPLES) {
      const params=await page.evaluate(()=>({preset:els.preset.value,background:els.backgroundColor.value,trim:Number(els.trim.value)/1000,opaque:Number(els.opaque.value)/1000,unmix:Number(els.unmix.value)/100,edgeClean:Number(els.edgeClean.value)/100,cloth:Number(els.cloth.value)/100}));
      await writeFile(path.join(dir,'settings.json'),JSON.stringify(params,null,2)+'\n');
    }
    console.log(`通过：${id} ${dims.width}×${dims.height} 文件导入、预设、预览与 PNG 下载`);
  }
  await page.selectOption('#previewMode','result');
  await page.locator('[data-view="dark"]').click();
  await mkdir(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results','web-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  assert.equal(overflow,false,'移动端页面水平溢出');
  await page.screenshot({path:path.join(root,'test-results','web-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('通过：透明/不透明/半透明像素、尺寸拒绝与显式缩放、窄屏布局、无页面异常。');
} finally { await browser.close(); }
