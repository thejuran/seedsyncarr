import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { of } from 'rxjs';
import * as Immutable from 'immutable';

import { SettingsPageComponent } from './settings-page.component';
import { LoggerService } from '../../services/utils/logger.service';
import { ConfigService } from '../../services/settings/config.service';
import { NotificationService } from '../../services/utils/notification.service';
import { ServerCommandService } from '../../services/server/server-command.service';
import { AutoQueueService } from '../../services/autoqueue/autoqueue.service';
import { ConnectedService } from '../../services/utils/connected.service';
import { StreamServiceRegistry } from '../../services/base/stream-service.registry';

describe('SettingsPageComponent', () => {
  let component: SettingsPageComponent;
  let fixture: ComponentFixture<SettingsPageComponent>;

  beforeEach(async () => {
    const mockConnectedService = jasmine.createSpyObj('ConnectedService', [], {
      connected: of(true)
    });

    const mockStreamServiceRegistry = jasmine.createSpyObj('StreamServiceRegistry', [], {
      connectedService: mockConnectedService
    });

    const mockConfigService = jasmine.createSpyObj('ConfigService', ['set', 'testSonarrConnection', 'testRadarrConnection'], {
      config: of(null)
    });

    const mockAutoQueueService = jasmine.createSpyObj('AutoQueueService', ['add', 'remove'], {
      patterns: of(Immutable.List())
    });

    await TestBed.configureTestingModule({
      imports: [SettingsPageComponent, FormsModule],
      providers: [
        { provide: LoggerService, useValue: jasmine.createSpyObj('LoggerService', ['info', 'error']) },
        { provide: StreamServiceRegistry, useValue: mockStreamServiceRegistry },
        { provide: ConfigService, useValue: mockConfigService },
        { provide: NotificationService, useValue: jasmine.createSpyObj('NotificationService', ['show', 'hide']) },
        { provide: ServerCommandService, useValue: jasmine.createSpyObj('ServerCommandService', ['restart']) },
        { provide: AutoQueueService, useValue: mockAutoQueueService },
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SettingsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('pending save state', () => {
    it('should initialize hasPendingChanges as false', () => {
      expect(component.hasPendingChanges).toBe(false);
    });

    it('should initialize saveConfirmed as false', () => {
      expect(component.saveConfirmed).toBe(false);
    });
  });

  describe('webhook copy state', () => {
    it('should initialize sonarrWebhookCopied as false', () => {
      expect(component.sonarrWebhookCopied).toBe(false);
    });

    it('should initialize radarrWebhookCopied as false', () => {
      expect(component.radarrWebhookCopied).toBe(false);
    });
  });
});
