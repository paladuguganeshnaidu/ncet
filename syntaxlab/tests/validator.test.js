'use strict';
const test=require('node:test'); const assert=require('node:assert/strict');
const {validate,results,server}=require('../server');
for(const [mode,input,expected] of require('../server').testcaseData){
  test(`${mode}: ${JSON.stringify(input)} => ${expected}`,()=>{const out=validate(mode,input);assert.equal(out.valid,expected);assert.ok(out.trace.length>0);assert.equal(out.trace.at(-1).to,expected?'qA':'qX');});
}
test('all built-in cases pass',()=>{assert.equal(results().filter(x=>!x.passed).length,0);});
test('invalid modes rejected by application helper',()=>assert.equal(validate('other','x'),null));
test('email local length is enforced',()=>assert.equal(validate('email','a'.repeat(65)+'@example.com').valid,false));
test('URL malformed percent escapes rejected',()=>assert.equal(validate('url','https://example.com/a%ZZ').valid,false));
test('embedded control characters rejected',()=>assert.equal(validate('url','https://example.com/\n').valid,false));
test('accepting traces always end in qA',()=>{for(const r of results()){const out=validate(r.mode,r.input);if(out.valid)assert.equal(out.trace.at(-1).to,'qA');}});