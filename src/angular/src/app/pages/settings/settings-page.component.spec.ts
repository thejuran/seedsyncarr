import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule } from "@angular/forms";
import { of } from "rxjs";
import * as Immutable from "immutable";

import { SettingsPageComponent } from "./settings-page.component";
import { LoggerService } from "../../services/utils/logger.service";
import { ConfigService } from "../../services/settings/config.service";
import { NotificationService } from "../../services/utils/notification.service";
import { ServerCommandService } from "../../services/server/server-command.service";
import { AutoQueueService } from "../../services/autoqueue/autoqueue.service";
import { PathPairsService } from "../../services/settings/path-pairs.service";
import { PathPair } from "../../services/settings/path-pair";
import { ConfirmModalService } from "../../services/utils/confirm-modal.service";
import { WebReaction } from "../../services/utils/rest.service";

import { StreamServiceRegistry } from "../../services/base/stream-service.registry";

describe("SettingsPageComponent", () => {
  let component: SettingsPageComponent;
  let fixture: ComponentFixture<SettingsPageComponent>;
  let mockPathPairsService: jasmine.SpyObj<PathPairsService>;
  let mockConfirmModal: jasmine.SpyObj<ConfirmModalService>;
  let mockNotifService: jasmine.SpyObj<NotificationService>;

  const legacyPair: PathPair = {
    id: "default", name: "Default", remote_path: "/r", local_path: "/l", enabled: true, auto_queue: true
  };
  const otherPair: PathPair = {
    id: "abc", name: "tv", remote_path: "/r/tv", local_path: "/l/tv", enabled: true, auto_queue: true
  };

  beforeEach(async () => {
    const mockConnectedService = jasmine.createSpyObj("ConnectedService", [], {
      connected: of(true)
    });

    const mockStreamServiceRegistry = jasmine.createSpyObj("StreamServiceRegistry", [], {
      connectedService: mockConnectedService
    });

    const mockConfigService = jasmine.createSpyObj("ConfigService", ["set", "testSonarrConnection", "testRadarrConnection"], {
      config: of(null)
    });

    const mockAutoQueueService = jasmine.createSpyObj("AutoQueueService", ["add", "remove"], {
      patterns: of(Immutable.List())
    });

    mockPathPairsService = jasmine.createSpyObj("PathPairsService", ["refresh", "create", "update", "remove"], {
      pairs: of([legacyPair, otherPair])
    });
    mockConfirmModal = jasmine.createSpyObj("ConfirmModalService", ["confirm"]);
    mockNotifService = jasmine.createSpyObj("NotificationService", ["show", "hide"]);

    await TestBed.configureTestingModule({
      imports: [SettingsPageComponent, FormsModule],
      providers: [
        { provide: LoggerService, useValue: jasmine.createSpyObj("LoggerService", ["info", "error"]) },
        { provide: StreamServiceRegistry, useValue: mockStreamServiceRegistry },
        { provide: ConfigService, useValue: mockConfigService },
        { provide: NotificationService, useValue: mockNotifService },
        { provide: ServerCommandService, useValue: jasmine.createSpyObj("ServerCommandService", ["restart"]) },
        { provide: AutoQueueService, useValue: mockAutoQueueService },
        { provide: PathPairsService, useValue: mockPathPairsService },
        { provide: ConfirmModalService, useValue: mockConfirmModal },
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SettingsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("pending save state", () => {
    it("should initialize hasPendingChanges as false", () => {
      expect(component.hasPendingChanges).toBe(false);
    });

    it("should initialize saveConfirmed as false", () => {
      expect(component.saveConfirmed).toBe(false);
    });
  });

  describe("webhook copy state", () => {
    it("should initialize sonarrWebhookCopied as false", () => {
      expect(component.sonarrWebhookCopied).toBe(false);
    });

    it("should initialize radarrWebhookCopied as false", () => {
      expect(component.radarrWebhookCopied).toBe(false);
    });
  });

  describe("path pairs", () => {
    const ok = new WebReaction(true, "{}", null);

    beforeEach(() => {
      component.commandsEnabled = true;
    });

    it("loads the pairs when the server is connected", () => {
      expect(mockPathPairsService.refresh).toHaveBeenCalled();
    });

    it("lists the pairs", () => {
      fixture.detectChanges();
      const names = Array.from<Element>(fixture.nativeElement.querySelectorAll(".pair-name")).map(e => e.textContent!.trim());
      expect(names).toEqual(["Default", "tv"]);
    });

    it("cannot save with an empty field", () => {
      component.pairForm = { name: "tv", remote_path: "", local_path: "/l" };
      expect(component.canSavePair).toBe(false);
      component.pairForm = { name: "tv", remote_path: "/r", local_path: "/l" };
      expect(component.canSavePair).toBe(true);
    });

    it("creates a pair, clears the form and shows the restart notice", () => {
      mockPathPairsService.create.and.returnValue(of(ok));
      component.pairForm = { name: " movies ", remote_path: "/r/m", local_path: "/l/m" };
      component.onSavePair();
      expect(mockPathPairsService.create).toHaveBeenCalledWith({ name: "movies", remote_path: "/r/m", local_path: "/l/m" });
      expect(component.pairForm).toEqual({ name: "", remote_path: "", local_path: "" });
      expect(mockNotifService.show).toHaveBeenCalled();
    });

    it("updates the pair being edited", () => {
      mockPathPairsService.update.and.returnValue(of(ok));
      component.onEditPair(otherPair);
      component.pairForm.name = "tv2";
      component.onSavePair();
      expect(mockPathPairsService.update).toHaveBeenCalledWith(
        "abc", { name: "tv2", remote_path: "/r/tv", local_path: "/l/tv" });
      expect(component.editingPairId).toBeNull();
    });

    it("sends only the name when editing the default pair", () => {
      mockPathPairsService.update.and.returnValue(of(ok));
      component.onEditPair(legacyPair);
      component.pairForm.name = "Main";
      component.onSavePair();
      expect(mockPathPairsService.update).toHaveBeenCalledWith("default", { name: "Main" });
    });

    it("shows the error and keeps the form when saving fails", () => {
      mockPathPairsService.create.and.returnValue(of(new WebReaction(false, null, "A path pair named 'x' already exists")));
      component.pairForm = { name: "x", remote_path: "/r", local_path: "/l" };
      component.onSavePair();
      expect(component.pairForm.name).toBe("x");
      expect(component.pairBusy).toBe(false);
      const notif = mockNotifService.show.calls.mostRecent().args[0];
      expect(notif.text).toContain("already exists");
    });

    it("toggles enabled and auto-queue", () => {
      mockPathPairsService.update.and.returnValue(of(ok));
      component.onTogglePair(otherPair, "enabled", false);
      component.onTogglePair(otherPair, "auto_queue", false);
      expect(mockPathPairsService.update).toHaveBeenCalledWith("abc", { enabled: false });
      expect(mockPathPairsService.update).toHaveBeenCalledWith("abc", { auto_queue: false });
    });

    it("deletes only after confirmation", async () => {
      mockPathPairsService.remove.and.returnValue(of(ok));
      mockConfirmModal.confirm.and.returnValue(Promise.resolve(false));
      await component.onDeletePair(otherPair);
      expect(mockPathPairsService.remove).not.toHaveBeenCalled();
      mockConfirmModal.confirm.and.returnValue(Promise.resolve(true));
      await component.onDeletePair(otherPair);
      expect(mockPathPairsService.remove).toHaveBeenCalledWith("abc");
    });
  });
});
