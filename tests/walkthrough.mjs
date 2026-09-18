import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
try {
 const page=await browser.newPage({viewport:{width:1400,height:1000}}), errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'walkthrough.html')).href);
 assert.equal(await page.locator('section').count(),6);
 for(const link of await page.locator('[href],img[src],iframe[src]').evaluateAll(es=>es.map(e=>e.getAttribute('href')||e.getAttribute('src')))){
   if(link.startsWith('#')){assert.equal(await page.locator(link).count(),1);continue;}
   if(!/^[a-z]+:/i.test(link))await access(path.resolve(root,link));
 }
 assert(await page.locator('img').evaluateAll(es=>es.every(e=>e.complete&&e.naturalWidth>0)));
 await page.locator('[data-copy="solidPrompt"]').click();
 // Clipboard writes settle asynchronously; wait for the copy or fallback UI.
 await page.locator('[data-copy="solidPrompt"]').filter({hasText:/已复制|已选中/}).waitFor();
 assert.match(await page.locator('[data-copy="solidPrompt"]').textContent(),/已复制|已选中/);
 await mkdir(path.join(root,'test-results'),{recursive:true});
 await page.screenshot({path:path.join(root,'test-results','walkthrough-desktop.png')});
 await page.locator('iframe').scrollIntoViewIfNeeded();
 const frame=page.frameLocator('iframe');
 await frame.locator('#colorInput').setInputFiles(path.join(root,'examples/pearl-gauze/solid.png'));
 await frame.locator('#maskInput').setInputFiles(path.join(root,'examples/pearl-gauze/alpha.png'));
 await frame.locator('#downloadBtn').waitFor();
 await frame.locator('#status').filter({hasText:'已生成 973×1616'}).waitFor();
 const pending=page.waitForEvent('download');
 await frame.locator('#downloadBtn').click();
 await (await pending).saveAs(path.join(root,'test-results','walkthrough-cutout.png'));
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>scrollTo(0,0));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:path.join(root,'test-results','walkthrough-mobile.png')});
 assert.deepEqual(errors,[]);
 console.log('PASS walkthrough: six steps, links, images, copy/fallback, embedded tool file import and PNG download, narrow layout, no JS errors');
}finally{await browser.close();}
