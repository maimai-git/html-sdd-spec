async page => {
 let checks=0;const ok=(value,message)=>{checks++;if(!value)throw new Error(message)};
 await page.reload();
 await page.setViewportSize({width:1600,height:1050});
 await page.getByRole('button',{name:'接口',exact:true}).click();
 await page.locator('#catalog [data-record]').first().click();
 const requests=page.locator('#detail .param-pane').first();
 const names=await requests.locator('tbody tr td:first-child').allTextContents();
 ok(JSON.stringify(names)==='["Authorization","folder_id","page","limit"]','公共字段展开顺序错误');
 ok((await requests.innerText()).includes('登录身份'),'公共字段说明丢失');
 ok((await requests.innerText()).includes('Bearer <token>'),'公共字段示例丢失');
 ok((await page.locator('#detail .param-pane').nth(1).locator('tbody tr').innerText()).includes('0'),'公共字段的0值不可见');
 await page.locator('#detail .rules-disclosure').click();
 ok((await page.locator('#detail .rules-disclosure li').allTextContents()).join('|')==='只读本人数据|企业须校验当前成员|接口自身约束','公共规则展开错误');
 ok((await page.locator('#detail .example-disclosure').first().innerText()).includes('business data, do not resolve'),'业务示例中的$ref被错误解析');
 const pointer=await page.locator('#catalog .catalog-path').first().textContent();
 ok(await page.evaluate(path=>{window.getSelection().removeAllRanges();return window.find(path,false,false,true)},pointer),'路径无法通过原生查找定位');
 const stored=await page.locator('#html-sdd-spec').textContent();
 ok(stored.includes('#/definitions/fields/身份~1~0'),'内嵌数据未保留引用');
 ok(stored.includes('"__proto__"'),'自有原型名称场景未覆盖');
 return {checks,offline:true};
}
