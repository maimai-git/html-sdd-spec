async page=>{
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.setViewportSize({width:1500,height:1000});await page.reload();
 for(const mode of ['requirements','apis','existingInterfaces','tables','architecture','configs']){
  await page.locator('[data-mode="'+mode+'"]').click();await page.locator('#catalog [data-record]').first().click();
  const name=await page.locator('#catalog .catalog-item.active .catalog-name').textContent();
  ok(await page.locator('#detail h1').count()===1,mode+'主标题数量错误');
  ok(await page.locator('#detail .card-head').count()===1,mode+'内容头部重复');
  ok(await page.locator('#detail h1').textContent()===name,mode+'标题与选择项不符');
  ok(await page.locator('#detail .page-head').count()===0,mode+'仍有外层重复标题');
  if(['apis','existingInterfaces'].includes(mode)){
   const path=await page.locator('#catalog .catalog-item.active .catalog-path').textContent();
   ok((await page.locator('#detail .card-head').innerText()).includes(path),'接口路径丢失');
   ok(await page.locator('#detail .param-pane').count()===2,'请求或响应参数丢失');
   const texts=await page.locator('#detail .card-body p').allTextContents();
   ok(!texts.some(text=>text.trim()===name.trim()),'接口摘要仍重复标题');
  }
 }
 await page.locator('[data-mode="architecture"]').click();
 const diagrams=page.locator('#catalog .catalog-item').filter({has:page.locator('.catalog-code',{hasText:/^图$/})});
 if(await diagrams.count()){
  await diagrams.first().click();
  ok(await page.locator('#detail h1').count()===1,'图形详情标题重复');
  ok((await page.locator('#detail').innerText()).includes('图源'),'图源丢失');
 }
 await page.locator('[data-mode="plan"]').click();
 ok(await page.locator('#detail h1').count()===1,'排期标题重复');
 ok(await page.locator('#detail .page-kicker,#detail .page-intro').count()===0,'排期仍有重复引导');
 return {checks,offline:true};
}
