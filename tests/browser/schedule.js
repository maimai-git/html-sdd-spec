async page=>{
 let checks=0;const ok=(x,msg)=>{checks++;if(!x)throw new Error(msg)};
 await page.setViewportSize({width:1600,height:1050});
 const url=new URL(page.url());if(!decodeURIComponent(url.pathname).endsWith('/目录筛选/方案对齐.html'))throw new Error('请先打开目录筛选示例');url.search='schedule=1';await page.goto(url.href);
 await page.getByRole('button',{name:'排期',exact:true}).click();
 const rows=()=>page.locator('tr[data-plan-id]').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.planId,seq:Number(n.cells[0].textContent),module:n.cells[2].querySelector('strong').textContent,color:[...n.classList].find(s=>/^module-/.test(s))})));
 let list=await rows();ok(JSON.stringify(list.map(x=>x.seq))==='[2,8,5,1]','默认模块排序错误');
 const colors=Object.fromEntries(list.map(x=>[x.module,x.color]));ok(list.every(x=>colors[x.module]===x.color),'同模块颜色不同');
 await page.getByLabel('按模块归类',{exact:true}).uncheck();ok(JSON.stringify((await rows()).map(x=>x.seq))==='[2,5,8,1]','优先级排序错误');
 await page.getByLabel('排期排序',{exact:true}).selectOption('sequence');ok(JSON.stringify((await rows()).map(x=>x.seq))==='[1,2,5,8]','序号排序错误');
 await page.getByLabel('排期排序',{exact:true}).selectOption('reverse');ok(JSON.stringify((await rows()).map(x=>x.seq))==='[1,8,2,5]','反向优先级排序错误');
 await page.getByLabel('排期状态',{exact:true}).selectOption('进行中');list=await rows();ok(list.length===1&&list[0].seq===2,'筛选后序号被重编');ok(list[0].color===colors[list[0].module],'筛选后模块颜色变化');
 await page.getByLabel('排期状态',{exact:true}).selectOption('待复核');ok((await rows()).length===0,'空筛选仍有旧行');ok((await page.locator('.plan-table').innerText()).includes('没有匹配任务'),'空态文案缺失');ok((await page.locator('.schedule-controls').innerText()).includes('0 / 4 项'),'空态计数错误');
 await page.getByLabel('排期状态',{exact:true}).selectOption('阻塞');await page.getByRole('button',{name:'接口',exact:true}).click();await page.getByRole('button',{name:'排期',exact:true}).click();ok(await page.getByLabel('排期状态',{exact:true}).inputValue()==='阻塞','切换分类丢失筛选');ok(!(await page.getByLabel('按模块归类',{exact:true}).isChecked()),'分组开关丢失');
 await page.getByRole('button',{name:'恢复默认',exact:true}).click();ok((await rows()).length===4,'恢复默认未还原任务');ok(await page.getByLabel('按模块归类',{exact:true}).isChecked(),'恢复默认未开启归类');
 await page.locator('[data-plan-toggle]').first().click();ok(await page.locator('.plan-details-row').first().isVisible(),'详情展开失败');ok(await page.locator('.plan-details-row td').first().getAttribute('colspan')==='7','详情列宽错误');ok(await page.locator('.plan-table th').count()===7,'表头列数错误');ok(!(await page.locator('#sidebar').isVisible()),'排期出现左菜单');
 const task=page.locator('[data-plan-toggle]').first();const taskName=await task.textContent();
 await task.click();ok(await task.textContent()===taskName,'收起后任务名丢失');ok(await task.getAttribute('aria-expanded')==='false','收起状态未同步');
 const req=page.locator('[data-plan-requirement]').first();if(await req.count()){const id=await req.getAttribute('data-plan-requirement');await req.click();ok((await page.locator('#detail h1').textContent()).length>0,'需求跳转无详情');ok(await page.locator('#catalog .catalog-item.active').getAttribute('data-record')===id,'需求跳转选中错误');await page.getByRole('button',{name:'排期',exact:true}).click()}
 await page.setViewportSize({width:1800,height:1050});await page.screenshot({path:'output/playwright/schedule.png'});return {checks,rows:await rows()};
}
