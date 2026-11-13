async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.reload();await page.locator('[data-mode="tables"]').click();
 const tables=await page.locator('#html-sdd-spec').evaluate(node=>JSON.parse(node.textContent).tables);
 for(const table of tables){
  await page.locator('[data-record="'+table.id+'"]').click();
  const title=table.name+(table.displayName?'（'+table.displayName.trim()+'）':'');
  ok(await page.locator('#detail h1').textContent()===title,'中英文表名未合并');
  ok(await page.locator('#catalog .catalog-item.active .catalog-name').textContent()===title,'菜单与详情表名不一致');
  const text=await page.locator('#detail .card-body').innerText();
  ok(!/表作用|当前状态|范围\/部署说明|结构差异/.test(text),'旧说明区块仍显示');
  ok(await page.locator('#detail .text-box').textContent()===(table.ddl||'-- 待补充'),'DDL被修改或丢失');
 }
 return {checks,offline:true};
}
