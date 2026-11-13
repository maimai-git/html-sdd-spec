async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width:1600,height:1050});await page.reload();
 await page.getByRole('button',{name:'排期',exact:true}).click();
 const plans=await page.locator('#html-sdd-spec').evaluate(node=>JSON.parse(node.textContent).plans);
 ok(JSON.stringify(await page.locator('.plan-table th').allTextContents())===JSON.stringify(['序号','优先级','模块 / 任务','关联需求','执行人','状态','进展与备注']),'表头不符合七列设计');
 ok(await page.locator('tr[data-plan-id]').count()===plans.length,'任务丢失');
 for(const p of plans){
  const actual=await page.locator('tr[data-plan-id]').evaluateAll((nodes,id)=>{const n=nodes.find(x=>x.dataset.planId===id);return {cells:[...n.cells].map(x=>x.textContent),note:n.cells[6].firstElementChild.title}},p.id);
  ok(actual.cells.length===7,'任务列数错误');
  ok(actual.cells[5]===p.status,'状态列错误');
  for(const v of [p.progress,p.note,p.blocker,p.statusNote].filter(x=>typeof x==='string'&&x.trim()))ok(actual.note.includes(v.trim()),'备注合并丢失信息');
 }
 const toggle=page.locator('[data-plan-toggle]').first(),name=await toggle.textContent();
 const links=page.locator('tr[data-plan-id] button[data-plan-toggle],tr[data-plan-id] button[data-plan-requirement]');
 ok(await links.evaluateAll(nodes=>nodes.every(node=>getComputedStyle(node).textDecorationLine==='none')),'排期列表按钮带有下划线');
 await toggle.hover();ok(await toggle.evaluate(node=>getComputedStyle(node).textDecorationLine)==='none','悬停显示下划线');
 await toggle.click();ok(await toggle.getAttribute('aria-expanded')==='true','点击任务不能展开');
 ok(await page.locator('.plan-details-row').first().isVisible(),'详情不可见');ok(await page.locator('.plan-details-row td').first().getAttribute('colspan')==='7','详情跨列错误');
 const noteFields=await page.locator('.plan-details-row').first().locator('.plan-detail b').allTextContents();
 ok(noteFields.filter(label=>label==='进展与备注').length<=1&&noteFields.every(label=>!['最新进度','备注','状态说明','阻塞原因'].includes(label)),'任务详情仍分开显示进展和备注');
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
