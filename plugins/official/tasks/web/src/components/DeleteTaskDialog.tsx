// SPDX-License-Identifier: MIT
// Delete with confirmation. Any adult may delete any task (decision D3).
import type { TaskOut } from "@hauskraft/sdk-ts";
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle, Icon } from "@hauskraft/ui";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useDeleteTask } from "../api";

export function DeleteTaskDialog({ task }: { task: TaskOut }) {
  const { t } = useTranslation("tasks");
  const remove = useDeleteTask();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={t("delete.button", { title: task.title })}
        onClick={() => setOpen(true)}
      >
        <Icon name="action.delete" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent showCloseButton={false}>
          <DialogTitle>{t("delete.title")}</DialogTitle>
          <DialogDescription>{t("delete.body", { title: task.title })}</DialogDescription>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              {t("delete.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                setOpen(false);
                await remove(task.id);
              }}
            >
              {t("delete.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
