async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.setViewportSize({width:1500,height:1000});await page.reload();
 for(const mode of ['requirements','apis','existingInterfaces','tables','architecture','configs']){
  await page.locator('[data-mode="'+mode+'"]').click();
  const items=page.locator('#catalog .catalog-item');ok(await items.count()>0,mode+'缺少验证条目');
  const results=await items.evaluateAll(nodes=>nodes.map(node=>{
   const name=node.querySelector('.catalog-name'),path=node.querySelector('.catalog-path'),tags=node.querySelector('.catalog-tags');
   const labels=tags?[...tags.children]:[];
   return {hasTags:!!tags,nameRight:name.getBoundingClientRect().right,itemRight:node.getBoundingClientRect().right,below:tags&&tags.getBoundingClientRect().top>=Math.max(name.getBoundingClientRect().bottom,path?path.getBoundingClientRect().bottom:0),first:labels[0]?.classList.contains('catalog-code'),last:labels.at(-1)?.classList.contains('catalog-status'),clipped:labels.some(n=>n.scrollWidth>n.clientWidth+1)};
  }));
  for(const r of results){ok(r.hasTags&&r.below,mode+'标签未统一放在内容下方');ok(r.first&&r.last,mode+'标签顺序不一致');ok(!r.clipped,mode+'标签文字被裁剪');ok(r.itemRight-r.nameRight<=12,mode+'名称没有使用整行宽度');}
 }
 return {checks,offline:true};
}
