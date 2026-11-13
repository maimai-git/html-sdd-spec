async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.setViewportSize({width:1500,height:1000});await page.reload();
 for(const mode of ['apis','existingInterfaces']){
  await page.locator('[data-mode="'+mode+'"]').click();
  const ids=await page.locator('#catalog [data-record]').evaluateAll(nodes=>nodes.map(n=>n.dataset.record));
  for(const id of ids){
   const item=page.locator('[data-record="'+id+'"]');await item.click();await item.hover();
   const box=await item.evaluate(node=>{
    const code=node.querySelector('.catalog-code'),name=node.querySelector('.catalog-name');
    const range=document.createRange();range.selectNodeContents(code);
    return {method:code.textContent,right:range.getBoundingClientRect().right,left:name.getBoundingClientRect().left,above:name.getBoundingClientRect().bottom<=code.getBoundingClientRect().top,methodClipped:code.scrollWidth>code.clientWidth+1,title:name.title,name:name.textContent};
   });
   ok(box.above||box.right+4<=box.left,box.method+' 标签遮挡接口名称');
   ok(!box.methodClipped,box.method+' 标签被截断');
   ok(box.title===box.name,'名称省略后缺少完整提示');
  }
  const path=await page.locator('#catalog .catalog-path').first().textContent();
  ok(await page.evaluate(value=>{window.getSelection().removeAllRanges();return window.find(value,false,false,true)},path),'完整路径无法原生搜索');
 }
 return {checks,offline:true};
}
