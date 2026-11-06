'use strict';
// Evidence status is a qualification, never a numerical confidence score.
const SEMANTICS=Object.freeze({
 VERIFIED:'A stated, applicable verification criterion was executed by an authorized verifier, with an attested result and no unresolved applicable contradiction.',
 SUPPORTED:'Applicable eligible evidence directly supports the exact proposition; an executed verification or sufficiency criterion is still missing.',
 PROVISIONAL:'Only indirect evidence or explicit assumptions provide conditional support; the conclusion is not verified.',
 CONTRADICTED:'Applicable, attested evidence contradicts the proposition. Conflicting support is retained and must be reviewed.',
 UNRESOLVED:'Evidence is missing, conflicting, ineligible, or insufficient for the requested conclusion. No evidence is not evidence of absence.',
 NOT_ASSESSED:'The claim has not yet undergone an evidence assessment.'
});
function status({assessed=false,direct=false,indirect=false,contradiction=false,conflict=false,criterionExecuted=false,authorizedReceipt=false}={}){
 if(!assessed)return 'NOT_ASSESSED';
 if(conflict)return 'UNRESOLVED';
 if(contradiction)return 'CONTRADICTED';
 if(direct&&criterionExecuted&&authorizedReceipt)return 'VERIFIED';
 if(direct)return 'SUPPORTED';
 if(indirect)return 'PROVISIONAL';
 return 'UNRESOLVED';
}
function transition(previous,facts){if(!Object.hasOwn(SEMANTICS,previous))throw Error('Unknown evidence status');return{from:previous,to:status(facts),basis:{...facts},qualification:'Reassessment uses the full current evidence set, never an unconditional promotion.'};}
module.exports={SEMANTICS,status,transition};
