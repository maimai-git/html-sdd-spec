async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width:1600,height:1050});await page.reload();
 await page.getByRole('button',{name:'排期',exact:true}).click();
 const plans=await page.locator('#html-sdd-spec').evaluate(node=>JSON.parse(node.textContent).plans);
 ok(JSON.stringify(await page.locator('.plan-table th').allTextContents())===JSON.stringify(['序号','优先级','模块 / 任务','关联需求','执行人','预计完成','状态','备注']),'表头不符合八列设计');
 ok(await page.locator('tr[data-plan-id]').count()===plans.length,'任务丢失');
 for(const p of plans){
  const actual=await page.locator('tr[data-plan-id]').evaluateAll((nodes,id)=>{const n=nodes.find(x=>x.dataset.planId===id);return {cells:[...n.cells].map(x=>x.textContent),note:n.cells[7].firstElementChild.title}},p.id);
  ok(actual.cells.length===8,'任务列数错误');
  const date=typeof p.end==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(p.end)?new Date(p.end+'T00:00:00Z'):null;
  const expected=date&&Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===p.end?p.end:'待定';
  ok(actual.cells[5]===expected,'预计完成错误');
  for(const v of [p.progress,p.note,p.blocker,p.statusNote].filter(x=>typeof x==='string'&&x.trim()))ok(actual.note.includes(v.trim()),'备注合并丢失信息');
 }
 const toggle=page.locator('[data-plan-toggle]').first(),name=await toggle.textContent();
 await toggle.click();ok(await toggle.getAttribute('aria-expanded')==='true','点击任务不能展开');
 ok(await page.locator('.plan-details-row').first().isVisible(),'详情不可见');ok(await page.locator('.plan-details-row td').first().getAttribute('colspan')==='8','详情跨列错误');
 await toggle.press('Enter');ok(await toggle.getAttribute('aria-expanded')==='false','键盘不能收起');ok(await toggle.textContent()===name,'展开后任务名称被覆盖');
 const requirement=page.locator('[data-plan-requirement]').first();
 if(await requirement.count()){
  const id=await requirement.getAttribute('data-plan-requirement');await requirement.click();
  ok(await page.locator('#catalog .active').getAttribute('data-record')===id,'需求跳转错误');
  await page.getByRole('button',{name:'排期',exact:true}).click();
 }
 ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'页面横向溢出');
 ok(errors.length===0,'浏览器脚本报错：'+errors.join('；'));
 await page.screenshot({path:'output/playwright/compact-schedule.png'});
 return {checks,tasks:plans.length,pageErrors:errors.length};
}
