import {installIngressRouting} from './ingress';
import {installReleaseExecution} from './releaseExecution';

installIngressRouting();
void import('./main').then(()=>installReleaseExecution());
