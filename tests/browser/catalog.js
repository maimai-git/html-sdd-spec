// Playwright CLI run-code；仅针对目录筛选示意数据，支持 file: 离线回归。
async page => {
  const demoUrl=page.url();
  if(!decodeURIComponent(new URL(demoUrl).pathname).endsWith("/目录筛选/方案对齐.html"))throw new Error("请先打开 examples/目录筛选/方案对齐.html");
  await page.setViewportSize({width:1440,height:1000});
  let checks=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const verify=(condition,message)=>{checks++;if(!condition)throw new Error(message)};
  const tab=name=>page.getByRole('button',{name,exact:true}).click();
  const apply=async(status,type)=>{await page.getByLabel('本期开发状态',{exact:true}).selectOption(status);await page.getByLabel('变更类型',{exact:true}).selectOption(type)};
  const ids=()=>page.locator('#catalog [data-record]').evaluateAll(rows=>rows.map(x=>x.dataset.record));
  const checkRows=async(expected,total)=>{
    verify(JSON.stringify(await ids())===JSON.stringify(expected),'目录结果不一致 '+expected);
    verify((await page.locator('#catalogCount').innerText())===`${expected.length} / ${total} 项`,'匹配计数不一致');
    if(!expected.length){verify((await page.locator('#detail').innerText())==='没有匹配条目','空结果未清空详情');verify(await page.locator('#catalog .active').count()===0,'空结果保留旧选中')}
    else verify((await page.locator('#detail .card-head').innerText()).includes(expected[0]),'详情不属于筛选结果');
  };
  await page.goto(demoUrl);
  await page.getByRole('heading',{name:'本期文件管理迭代',level:1}).waitFor();
  await tab('接口');
  const cases=[['','',['API-001','API-002','API-003','API-004']],['已完成','new',['API-001']],['部分完成','changed',['API-002']],['未开发','reused',['API-003']],['已完成','existing',[]],['待核实','new',['API-004']],['','existing',['API-002','API-003']],['','reused',['API-003']],['部分完成','new',[]]];
  for(const [status,type,expected] of cases){await apply(status,type);await checkRows(expected,4)}
  await apply('部分完成','changed');
  verify((await page.locator('#detail .tag-list .status').innerText())==='部分完成','开发状态从部署文案猜测');
  verify((await page.locator('.delivery-note').innerText()).includes('标签同步尚未完成'),'部署/范围说明丢失');
  await tab('数据表');
  verify(await page.getByLabel('本期开发状态',{exact:true}).inputValue()==='','表继承了接口筛选');
  for(const [status,type,expected] of [['已完成','new',['DATA-001']],['未开发','existing',['DATA-002']],['部分完成','reused',['DATA-003']],['已完成','reused',[]]]){await apply(status,type);await checkRows(expected,3)}
  await apply('未开发','existing');
  await tab('接口');
  verify(await page.getByLabel('本期开发状态',{exact:true}).inputValue()==='部分完成','接口状态未保留');
  verify(await page.getByLabel('变更类型',{exact:true}).inputValue()==='changed','接口类型未保留');
  await tab('现有相关接口梳理');
  verify(await page.locator('[data-catalog-filter]').count()===0,'master接口被混入筛选');
  verify(await page.locator('#catalog [data-record]').count()===1,'master接口数量被修改');
  await tab('数据表');
  verify(await page.getByLabel('本期开发状态',{exact:true}).inputValue()==='未开发','表状态未保留');
  await page.getByRole('button',{name:'恢复全部',exact:true}).click();await checkRows(['DATA-001','DATA-002','DATA-003'],3);
  const ddl=page.locator('.text-disclosure');verify(await ddl.evaluate(e=>e.open),'DDL未默认展开');
  await ddl.locator('summary').click();verify(!(await ddl.evaluate(e=>e.open)),'DDL不能手动收起');
  verify(!(await page.getByText('结构差异',{exact:true}).evaluate(e=>e.parentElement.open)),'其他折叠项被展开');
  await tab('接口');
  verify(await page.getByLabel('本期开发状态',{exact:true}).inputValue()==='部分完成','恢复表筛选清掉了接口筛选');
  await page.getByRole('button',{name:'恢复全部',exact:true}).click();await checkRows(['API-001','API-002','API-003','API-004'],4);
  verify((await page.locator('.example-disclosure').evaluateAll(nodes=>nodes.every(e=>e.open))),'请求/响应实例未默认展开');
  await page.locator('.example-disclosure').first().locator('summary').click();verify(!(await page.locator('.example-disclosure').first().evaluate(e=>e.open)),'实例不能手动收起');
  const find=await page.evaluate(()=>{
    window.getSelection().removeAllRanges();const found=window.find('native-find-tail',false,false,true,false,false,false);
    const node=window.getSelection().anchorNode;const element=node?.nodeType===3?node.parentElement:node;
    const path=document.querySelector('[data-record="API-004"] .catalog-path');
    return {found,id:element?.closest('[data-record]')?.dataset.record,full:path?.textContent,title:path?.title,clipped:path.scrollWidth>path.clientWidth};
  });
  verify(find.found&&find.id==='API-004','截断路径尾部无法原生搜索定位');
  verify(find.full===find.title&&find.clipped,'路径不是单行省略并保留全文提示');
  await page.locator('#catalog [data-record="API-004"]').click();verify((await page.locator('#detail').innerText()).includes(find.full),'找到路径后不能点开对应详情');
  await page.getByRole('button',{name:'恢复全部',exact:true}).click();
  const before=await page.locator('main').boundingBox();
  await page.locator('.snapshot-version > summary').click();
  await page.waitForFunction(()=>document.querySelector('.snapshot-version').open);
  verify(Math.abs((await page.locator('main').boundingBox()).y-before.y)<1,'版本展开推高正文');
  await page.locator('.readiness-summary').click();
  await page.waitForFunction(()=>document.querySelector('.readiness-card').open&&!document.querySelector('.snapshot-version').open);
  verify(Math.abs((await page.locator('main').boundingBox()).y-before.y)<1,'编码条件展开推高正文');
  await page.keyboard.press('Escape');verify(await page.locator('#snapshot > details[open]').count()===0,'Esc不能关闭弹层');
  await page.locator('.snapshot-version > summary').click();await page.mouse.click(page.viewportSize().width-24,page.viewportSize().height-24);verify(await page.locator('#snapshot > details[open]').count()===0,'外部点击不能关闭弹层');
  await page.setViewportSize({width:1100,height:900});await page.locator('.readiness-summary').click();
  const rect=await page.locator('.readiness-card .snapshot-panel').boundingBox();verify(rect.x>=0&&rect.x+rect.width<=1100,'弹层在窄桌面越界');
  await page.keyboard.press('Escape');await page.setViewportSize({width:1440,height:1000});
  const metrics=await page.evaluate(()=>({summaryHeight:document.querySelector('#snapshot').getBoundingClientRect().height,itemHeight:document.querySelector('.catalog-item').getBoundingClientRect().height,bodyFont:getComputedStyle(document.querySelector('.section p')).fontSize}));
  await page.screenshot({path:'output/playwright/catalog.png'});
  await tab('上线需要配置');verify(!(await page.locator('body').innerText()).includes('只展示需要填写或执行的文本'),'指定提示仍存在');verify((await page.locator('#detail').innerText()).includes('执行来源'),'配置执行源未展示');
  await tab('排期');verify(!(await page.locator('#sidebar').isVisible()),'排期仍有左菜单');await page.getByRole('button',{name:'详情',exact:true}).first().click();verify(await page.locator('.plan-details-row').first().isVisible(),'排期详情失效');
  await page.goto(new URL('../asset-library/index.html',demoUrl).href);await tab('接口');
  verify(await page.locator('#catalog .catalog-status').evaluateAll(nodes=>nodes.every(e=>e.textContent==='待核实')),'历史快照被猜成开发完成');
  await page.getByLabel('本期开发状态',{exact:true}).selectOption('已完成');verify((await page.locator('#detail').innerText())==='没有匹配条目','旧数据被错误纳入已完成');
  await page.getByRole('button',{name:'恢复全部',exact:true}).click();verify(await page.locator('#catalog [data-record]').count()===await page.evaluate(()=>window.__HTML_SDD__.apis.length),'旧数据恢复后丢失');
  await page.goto(demoUrl);await tab('接口');
  verify(errors.length===0,'页面错误 '+errors.join(';'));
  return {checks,metrics,nativeFind:find.id,offline:new URL(demoUrl).protocol==="file:",errors};
}
