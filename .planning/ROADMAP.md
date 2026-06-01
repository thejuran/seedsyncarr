
**Plans**: 2 plans (1 wave)
- [ ] 103-01-PLAN.md — BUG-01: replace the ConfirmModalService innerHTML sink with Renderer2 structural (createText) DOM construction, remove dead escapeHtml/safe* locals, fold in Number(skipCount) coercion; update the slice-1 XSS suite (structural assertions) + invert the D-05 runtime-boundary probe (test-first red→green) (wave 1)
- [ ] 103-02-PLAN.md — BUG-04: unsubscribe _currentSubscription at the top of reconnectDueToTimeout() (mirrors the createSseObserver entry teardown) so a same-tick timeout+error collision leaves exactly one EventSource; add the same-tick collision regression test, preserve the slice-1 heartbeat-vs-timeout race suite (test-first red→green) (wave 1)

**UI hint**: yes
