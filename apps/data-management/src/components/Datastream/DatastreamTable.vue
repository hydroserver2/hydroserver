<template>
  <h6 class="text-h6" style="color: #b71c1c">
    {{ thing!.dataDisclaimer }}
  </h6>

  <v-card ref="datastreamSectionRef">
    <div class="datastream-toolbar">
      <div class="datastream-toolbar__left">
        <h5 class="text-h6 datastream-toolbar__title">
          Datastreams available at this site
        </h5>
        <v-text-field
          v-model="search"
          clearable
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          hide-details
          density="compact"
          variant="underlined"
          rounded="xl"
          class="datastream-search ml-2"
        />
      </div>
      <div class="datastream-toolbar__actions">
        <v-btn
          color="white"
          variant="outlined"
          :prependIcon="mdiChartLine"
          :to="{ name: 'VisualizeData', query: { sites: thing!.id } }"
          >View on Data Visualization Page</v-btn
        >
        <v-btn-add
          v-if="
            hasPermission(
              PermissionResource.Datastream,
              PermissionAction.Create,
              workspace
            )
          "
          color="white"
          :prependIcon="mdiPlus"
          data-testid="add-datastream-button"
          @click="openCreate = true"
          >Add new datastream</v-btn-add
        >
      </div>
    </div>

    <div v-if="isMobile" class="datastream-mobile-list">
      <v-card
        v-for="item in mobileDatastreams"
        :key="item.id"
        class="datastream-card"
        :class="{
          'datastream-card--highlighted': isTargetDatastream(item.id),
        }"
        :data-datastream-id="item.id"
        variant="outlined"
      >
        <div class="datastream-card__content">
          <div class="datastream-card__title">
            {{ item.name || item.OPName }}
          </div>
          <div
            v-if="
              !hasPermission(
                PermissionResource.Datastream,
                PermissionAction.View,
                workspace
              ) && !item.isVisible
            "
            class="text-body-2"
          >
            Data is private for this datastream
          </div>
          <div v-else>
            <Sparkline
              class="mt-1"
              :datastream="item"
              @openChart="openCharts[item.id] = true"
              @latest-value="(value) => handleLatestValueUpdate(item.id, value)"
              :unitName="item.unitName"
            />
            <div
              v-if="Number(item.valueCount) > 0"
              class="mt-1 text-base leading-[1.3]"
              :class="latestStatusClass(item)"
            >
              <strong class="mr-2 font-semibold">Latest observation:</strong>
              <span class="font-semibold">{{ item.endDate }}</span>
            </div>
            <div
              v-if="shouldShowLatestValue(item.id)"
              class="mt-1 text-base leading-[1.3]"
              :class="latestStatusClass(item)"
            >
              <strong class="mr-2 font-semibold">Latest value:</strong>
              <span class="font-semibold">{{ latestValueDisplay(item) }}</span>
            </div>
          </div>

          <v-dialog v-model="openCharts[item.id]" width="80rem">
            <DatastreamPopupPlot
              :datastream="item"
              @close="openCharts[item.id] = false"
            />
          </v-dialog>

          <div class="datastream-info-list">
            <p class="datastream-line">
              <strong class="mr-2">Identifier:</strong>
              <span class="datastream-id">
                {{ item.id }}
                <v-tooltip text="Copy ID">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon
                      size="default"
                      variant="text"
                      class="datastream-copy-btn"
                      @click.stop="copyDatastreamId(item.id)"
                    >
                      <v-icon :icon="mdiContentCopy" size="small" />
                    </v-btn>
                  </template>
                </v-tooltip>
              </span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Sampled medium:</strong>
              <span>{{ item.sampledMedium }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Method:</strong>
              <span>{{ item.sensorName }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">No data value:</strong>
              <span>{{ item.noDataValue }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Begin date:</strong>
              <span>{{ item.beginDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">End date:</strong>
              <span>{{ item.endDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Number of observations:</strong>
              <span>{{ item.valueCount }}</span>
            </p>
          </div>
          <div
            v-if="canViewOrchestrationInfo && linkedTasksLoaded"
            class="datastream-task-link"
            :class="datastreamTaskLinkClass(item.id)"
          >
            <v-icon
              :class="[
                'datastream-task-link__icon',
                linkedTasksForDatastream(item.id).length === 1
                  ? linkedTasksForDatastream(item.id)[0].iconClass
                  : '',
              ]"
              :icon="
                !linkedTasksForDatastream(item.id).length
                  ? mdiLinkOff
                  : linkedTasksForDatastream(item.id).length > 1
                  ? mdiAlertOctagon
                  : linkedTasksForDatastream(item.id)[0].icon
              "
              size="20"
            />
            <div class="datastream-task-link__body">
              <div class="datastream-task-link__meta">
                <span class="datastream-task-link__label">
                  {{
                    linkedTasksForDatastream(item.id).length > 1
                      ? 'Multiple task targets'
                      : linkedTasksForDatastream(item.id).length === 1
                      ? linkedTasksForDatastream(item.id)[0].label
                      : 'No task connected'
                  }}
                </span>
                <template v-if="linkedTasksForDatastream(item.id).length === 1">
                  <RouterLink
                    class="datastream-task-link__name"
                    :to="linkedTasksForDatastream(item.id)[0].route"
                  >
                    {{ linkedTasksForDatastream(item.id)[0].displayName }}
                  </RouterLink>
                  <span
                    class="datastream-task-link__status"
                    :title="
                      displayedTaskStatus(linkedTasksForDatastream(item.id)[0])
                    "
                  >
                    <span
                      class="datastream-task-link__dot"
                      :style="{
                        backgroundColor: taskStatusColor(
                          linkedTasksForDatastream(item.id)[0]
                        ),
                      }"
                    />
                    <span class="datastream-task-link__last-ran">
                      {{ lastRanLabel(linkedTasksForDatastream(item.id)[0]) }}
                    </span>
                  </span>
                </template>
                <span v-else class="datastream-task-link__conflict-text">
                  {{
                    linkedTasksForDatastream(item.id).length > 1
                      ? `${
                          linkedTasksForDatastream(item.id).length
                        } tasks are feeding this datastream.`
                      : ''
                  }}
                </span>
              </div>
              <div
                v-if="linkedTasksForDatastream(item.id).length > 1"
                class="datastream-task-link__tasks"
              >
                <RouterLink
                  v-for="task in linkedTasksForDatastream(item.id)"
                  :key="task.id"
                  :to="task.route"
                >
                  {{ task.displayName }}
                </RouterLink>
              </div>
            </div>
            <v-btn
              v-if="linkedTasksForDatastream(item.id).length === 1"
              size="small"
              variant="text"
              color="primary"
              :append-icon="mdiChevronRight"
              :to="linkedTasksForDatastream(item.id)[0].route"
            >
              Manage
            </v-btn>
          </div>
          <div
            v-else-if="showTaskSkeleton"
            class="datastream-task-link datastream-task-link--loading"
            aria-label="Loading task information"
          >
            <span class="datastream-task-link__loading-icon" />
            <div class="datastream-task-link__body">
              <span
                class="datastream-task-link__loading-bar datastream-task-link__loading-bar--label"
              />
              <span
                class="datastream-task-link__loading-bar datastream-task-link__loading-bar--name"
              />
            </div>
          </div>
        </div>
        <div class="datastream-card__actions">
          <div class="datastream-card__icons">
            <v-tooltip
              bottom
              :openDelay="500"
              content-class="pa-0 ma-0 bg-transparent"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
            >
              <template #activator="{ props: tp }">
                <v-icon
                  v-bind="tp"
                  :icon="item.isVisible ? mdiFileEyeOutline : mdiFileRemove"
                  :color="item.isVisible ? 'green' : 'red-darken-2'"
                  :data-testid="`data-visibility-toggle-${item.id}`"
                  small
                  @click="toggleDataVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Observations are currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isVisible
                      ? 'Hide data for this datastream from guests of your site while keeping the datastream metadata publicly visible.'
                      : 'Make the observations and metadata for this datastream visible to guests of your site.',
                  },
                ]"
                :is-visible="item.isVisible"
              />
            </v-tooltip>

            <v-tooltip
              bottom
              :openDelay="500"
              v-if="
                hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.Edit,
                  workspace
                )
              "
              content-class="pa-0 ma-0 bg-transparent"
            >
              <template v-slot:activator="{ props }">
                <v-icon
                  :icon="item.isPrivate ? mdiLock : mdiLockOpenVariant"
                  :color="item.isPrivate ? 'red-darken-2' : 'green'"
                  :data-testid="`datastream-privacy-toggle-${item.id}`"
                  small
                  v-bind="props"
                  @click="toggleVisibility(item)"
                />
              </template>

              <VisibilityTooltipCard
                title="Datastream is currently"
                :items="[
                  {
                    label: 'Clicking this will',
                    value: item.isPrivate
                      ? 'Make this datastream and all its metadata and observations publicly visible.'
                      : 'Hide this datastream from guests of your site along with all its metadata and observations.',
                  },
                ]"
                :is-visible="!item.isPrivate"
              />
            </v-tooltip>

            <v-tooltip
              v-if="
                !hasPermission(
                  PermissionResource.Datastream,
                  PermissionAction.View,
                  workspace
                ) && !item.isVisible
              "
              bottom
              :openDelay="100"
            >
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" :icon="mdiLock" color="red-darken-2" />
              </template>
              <span>The data for this datastream is private </span>
            </v-tooltip>

            <v-menu v-else>
              <template v-slot:activator="{ props }">
                <v-icon
                  v-bind="props"
                  :icon="mdiDotsVertical"
                  :data-testid="`datastream-actions-${item.id}`"
                />
              </template>
              <v-list>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Edit,
                      workspace
                    )
                  "
                  :prepend-icon="mdiPencil"
                  title="Edit datastream metadata"
                  :data-testid="`edit-datastream-${item.id}`"
                  @click="openDialog(item, 'edit')"
                />
                <div
                  v-if="
                    hasPermission(
                      PermissionResource.Datastream,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                >
                  <v-list-item
                    :prepend-icon="mdiDelete"
                    title="Delete datastream"
                    :data-testid="`delete-datastream-${item.id}`"
                    @click="openDialog(item, 'delete')"
                  />
                </div>
                <v-list-item
                  v-if="
                    hasPermission(
                      PermissionResource.Observation,
                      PermissionAction.Delete,
                      workspace
                    )
                  "
                  :prepend-icon="mdiDeleteOutline"
                  title="Delete data from datastream"
                  :data-testid="`delete-datastream-data-${item.id}`"
                  @click="openObservationDialog(item)"
                />
                <v-list-item
                  :prepend-icon="mdiChartLine"
                  title="Visualize data"
                  :data-testid="`visualize-datastream-${item.id}`"
                  :to="{
                    name: 'VisualizeData',
                    query: { sites: item.thingId, datastreams: item.id },
                  }"
                />
                <v-list-item
                  :prepend-icon="mdiDownload"
                  title="Download data"
                  :data-testid="`download-datastream-${item.id}`"
                  @click="onDownload(item.id)"
                />
              </v-list>
            </v-menu>
          </div>
          <v-btn
            variant="outlined"
            class="datastream-card__meta-btn"
            :data-testid="`datastream-metadata-${item.id}`"
            @click="openInfoCardFor(item)"
          >
            View Full Metadata
          </v-btn>
          <div v-if="downloading[item.id]" class="datastream-download mt-2">
            <v-progress-circular
              indeterminate
              size="16"
              width="2"
              color="primary"
            />
            preparing file...
          </div>
        </div>
      </v-card>
    </div>

    <div v-else class="datastream-list">
      <div class="datastream-list__head">
        <span>Observation information</span>
        <span>Datastream information</span>
        <span class="datastream-list__head-actions">Actions</span>
      </div>

      <div
        v-for="item in tableDatastreams"
        :key="item.id"
        class="ds-card"
        :class="{ 'ds-card--highlighted': isTargetDatastream(item.id) }"
        :data-datastream-id="item.id"
      >
        <div class="ds-card__grid">
          <div class="datastream-latest">
            <div class="datastream-title">
              {{ item.name || item.OPName }}
            </div>
            <div class="mt-1">
              <div
                v-if="
                  !hasPermission(
                    PermissionResource.Datastream,
                    PermissionAction.View,
                    workspace
                  ) && !item.isVisible
                "
                class="text-body-2"
              >
                Data is private for this datastream
              </div>
              <div v-else>
                <Sparkline
                  class="mt-1"
                  :datastream="item"
                  @openChart="openCharts[item.id] = true"
                  @latest-value="
                    (value) => handleLatestValueUpdate(item.id, value)
                  "
                  :unitName="item.unitName"
                />
                <div
                  v-if="Number(item.valueCount) > 0"
                  class="mt-1 text-base leading-[1.3]"
                  :class="latestStatusClass(item)"
                >
                  <strong class="mr-2 font-semibold"
                    >Latest observation:</strong
                  >
                  <span class="font-semibold">{{ item.endDate }}</span>
                </div>
                <div
                  v-if="shouldShowLatestValue(item.id)"
                  class="mt-1 text-base leading-[1.3]"
                  :class="latestStatusClass(item)"
                >
                  <strong class="mr-2 font-semibold">Latest value:</strong>
                  <span class="font-semibold">{{
                    latestValueDisplay(item)
                  }}</span>
                </div>
              </div>
            </div>

            <v-dialog v-model="openCharts[item.id]" width="80rem">
              <DatastreamPopupPlot
                :datastream="item"
                @close="openCharts[item.id] = false"
              />
            </v-dialog>
          </div>
          <div class="datastream-info-list">
            <p class="datastream-line">
              <strong class="mr-2">Identifier:</strong>
              <span class="datastream-id">
                {{ item.id }}
                <v-tooltip text="Copy ID">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon
                      size="small"
                      variant="text"
                      @click.stop="copyDatastreamId(item.id)"
                    >
                      <v-icon :icon="mdiContentCopy" size="small" />
                    </v-btn>
                  </template>
                </v-tooltip>
              </span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Sampled medium:</strong>
              <span>{{ item.sampledMedium }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Method:</strong>
              <span>{{ item.sensorName }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">No data value:</strong>
              <span>{{ item.noDataValue }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Begin date:</strong>
              <span>{{ item.beginDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">End date:</strong>
              <span>{{ item.endDate }}</span>
            </p>
            <p class="datastream-line">
              <strong class="mr-2">Number of observations:</strong>
              <span>{{ item.valueCount }}</span>
            </p>
          </div>
          <div class="datastream-actions">
            <div class="datastream-actions__icons">
              <v-tooltip
                bottom
                :openDelay="500"
                content-class="pa-0 ma-0 bg-transparent"
                v-if="
                  hasPermission(
                    PermissionResource.Datastream,
                    PermissionAction.Edit,
                    workspace
                  )
                "
              >
                <template #activator="{ props: tp }">
                  <v-icon
                    v-bind="tp"
                    :icon="item.isVisible ? mdiFileEyeOutline : mdiFileRemove"
                    :color="item.isVisible ? 'green' : 'red-darken-2'"
                    :data-testid="`data-visibility-toggle-${item.id}`"
                    small
                    @click="toggleDataVisibility(item)"
                  />
                </template>

                <VisibilityTooltipCard
                  title="Observations are currently"
                  :items="[
                    {
                      label: 'Clicking this will',
                      value: item.isVisible
                        ? 'Hide data for this datastream from guests of your site while keeping the datastream metadata publicly visible.'
                        : 'Make the observations and metadata for this datastream visible to guests of your site.',
                    },
                  ]"
                  :is-visible="item.isVisible"
                />
              </v-tooltip>

              <v-tooltip
                bottom
                :openDelay="500"
                v-if="
                  hasPermission(
                    PermissionResource.Datastream,
                    PermissionAction.Edit,
                    workspace
                  )
                "
                content-class="pa-0 ma-0 bg-transparent"
              >
                <template v-slot:activator="{ props }">
                  <v-icon
                    :icon="item.isPrivate ? mdiLock : mdiLockOpenVariant"
                    :color="item.isPrivate ? 'red-darken-2' : 'green'"
                    :data-testid="`datastream-privacy-toggle-${item.id}`"
                    small
                    v-bind="props"
                    @click="toggleVisibility(item)"
                  />
                </template>

                <VisibilityTooltipCard
                  title="Datastream is currently"
                  :items="[
                    {
                      label: 'Clicking this will',
                      value: item.isPrivate
                        ? 'Make this datastream and all its metadata and observations publicly visible.'
                        : 'Hide this datastream from guests of your site along with all its metadata and observations.',
                    },
                  ]"
                  :is-visible="!item.isPrivate"
                />
              </v-tooltip>

              <v-tooltip
                v-if="
                  !hasPermission(
                    PermissionResource.Datastream,
                    PermissionAction.View,
                    workspace
                  ) && !item.isVisible
                "
                bottom
                :openDelay="100"
              >
                <template v-slot:activator="{ props }">
                  <v-icon v-bind="props" :icon="mdiLock" color="red-darken-2" />
                </template>
                <span>The data for this datastream is private </span>
              </v-tooltip>

              <v-menu v-else>
                <template v-slot:activator="{ props }">
                  <v-icon
                    v-bind="props"
                    :icon="mdiDotsVertical"
                    :data-testid="`datastream-actions-${item.id}`"
                  />
                </template>
                <v-list>
                  <v-list-item
                    v-if="
                      hasPermission(
                        PermissionResource.Datastream,
                        PermissionAction.Edit,
                        workspace
                      )
                    "
                    :prepend-icon="mdiPencil"
                    title="Edit datastream metadata"
                    :data-testid="`edit-datastream-${item.id}`"
                    @click="openDialog(item, 'edit')"
                  />
                  <div
                    v-if="
                      hasPermission(
                        PermissionResource.Datastream,
                        PermissionAction.Delete,
                        workspace
                      )
                    "
                  >
                    <v-list-item
                      :prepend-icon="mdiDelete"
                      title="Delete datastream"
                      :data-testid="`delete-datastream-${item.id}`"
                      @click="openDialog(item, 'delete')"
                    />
                  </div>
                  <v-list-item
                    v-if="
                      hasPermission(
                        PermissionResource.Observation,
                        PermissionAction.Delete,
                        workspace
                      )
                    "
                    :prepend-icon="mdiDeleteOutline"
                    title="Delete data from datastream"
                    :data-testid="`delete-datastream-data-${item.id}`"
                    @click="openObservationDialog(item)"
                  />
                  <v-list-item
                    :prepend-icon="mdiChartLine"
                    title="Visualize data"
                    :data-testid="`visualize-datastream-${item.id}`"
                    :to="{
                      name: 'VisualizeData',
                      query: { sites: item.thingId, datastreams: item.id },
                    }"
                  />
                  <v-list-item
                    :prepend-icon="mdiDownload"
                    title="Download data"
                    :data-testid="`download-datastream-${item.id}`"
                    @click="onDownload(item.id)"
                  />
                </v-list>
              </v-menu>
            </div>
            <v-btn
              variant="outlined"
              class="mt-2 datastream-meta-btn"
              :data-testid="`datastream-metadata-${item.id}`"
              @click="openInfoCardFor(item)"
            >
              View Full Metadata
            </v-btn>
            <div v-if="downloading[item.id]" class="datastream-download mt-2">
              <v-progress-circular
                indeterminate
                size="16"
                width="2"
                color="primary"
              />
              preparing file...
            </div>
          </div>
        </div>

        <div
          v-if="showTaskRow"
          class="datastream-task-link datastream-task-link--card"
          :class="datastreamTaskLinkClass(item.id)"
        >
          <v-icon
            :class="[
              'datastream-task-link__icon',
              linkedTasksForDatastream(item.id).length === 1
                ? linkedTasksForDatastream(item.id)[0].iconClass
                : '',
            ]"
            :icon="
              !linkedTasksForDatastream(item.id).length
                ? mdiLinkOff
                : linkedTasksForDatastream(item.id).length > 1
                ? mdiAlertOctagon
                : linkedTasksForDatastream(item.id)[0].icon
            "
            size="20"
          />
          <div class="datastream-task-link__body">
            <div class="datastream-task-link__meta">
              <span class="datastream-task-link__label">
                {{
                  linkedTasksForDatastream(item.id).length > 1
                    ? 'Multiple task targets'
                    : linkedTasksForDatastream(item.id).length === 1
                    ? linkedTasksForDatastream(item.id)[0].label
                    : 'No task connected'
                }}
              </span>
              <template v-if="linkedTasksForDatastream(item.id).length === 1">
                <RouterLink
                  class="datastream-task-link__name"
                  :to="linkedTasksForDatastream(item.id)[0].route"
                >
                  {{ linkedTasksForDatastream(item.id)[0].displayName }}
                </RouterLink>
                <span
                  class="datastream-task-link__status"
                  :title="
                    displayedTaskStatus(linkedTasksForDatastream(item.id)[0])
                  "
                >
                  <span
                    class="datastream-task-link__dot"
                    :style="{
                      backgroundColor: taskStatusColor(
                        linkedTasksForDatastream(item.id)[0]
                      ),
                    }"
                  />
                  <span class="datastream-task-link__last-ran">
                    {{ lastRanLabel(linkedTasksForDatastream(item.id)[0]) }}
                  </span>
                </span>
              </template>
              <span v-else class="datastream-task-link__conflict-text">
                {{
                  linkedTasksForDatastream(item.id).length > 1
                    ? `${
                        linkedTasksForDatastream(item.id).length
                      } tasks are feeding this datastream.`
                    : ''
                }}
              </span>
            </div>
            <div
              v-if="linkedTasksForDatastream(item.id).length > 1"
              class="datastream-task-link__tasks"
            >
              <RouterLink
                v-for="task in linkedTasksForDatastream(item.id)"
                :key="task.id"
                :to="task.route"
              >
                {{ task.displayName }}
              </RouterLink>
            </div>
          </div>
          <v-btn
            v-if="linkedTasksForDatastream(item.id).length === 1"
            size="small"
            variant="text"
            color="primary"
            :append-icon="mdiChevronRight"
            :to="linkedTasksForDatastream(item.id)[0].route"
          >
            Manage
          </v-btn>
        </div>
        <div
          v-else-if="showTaskSkeleton"
          class="datastream-task-link datastream-task-link--card datastream-task-link--loading"
          aria-label="Loading task information"
        >
          <span class="datastream-task-link__loading-icon" />
          <div class="datastream-task-link__body">
            <span
              class="datastream-task-link__loading-bar datastream-task-link__loading-bar--label"
            />
            <span
              class="datastream-task-link__loading-bar datastream-task-link__loading-bar--name"
            />
          </div>
        </div>
      </div>
    </div>
  </v-card>

  <v-dialog v-model="openCreate" width="80rem">
    <DatastreamForm
      :thing="thing!"
      :workspace="workspace"
      @close="openCreate = false"
      @created="onCreated"
    />
  </v-dialog>

  <v-dialog v-model="openEdit" width="80rem">
    <DatastreamForm
      :thing="thing!"
      :workspace="workspace"
      :datastream="item"
      @close="openEdit = false"
      @updated="updateDatastream"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DatastreamDeleteCard
      :datastream="item"
      @close="openDelete = false"
      @delete="onDelete"
    />
  </v-dialog>

  <v-dialog v-model="openObservationsDelete" width="40rem">
    <ObservationsDeleteCard
      :datastream="item"
      @close="openObservationsDelete = false"
      @delete="onObservationsDelete"
    />
  </v-dialog>

  <v-dialog
    v-model="openInfoCard"
    width="50rem"
    v-if="selectedDatastream && thing"
  >
    <DatastreamTableInfoCard
      :datastream="selectedDatastream"
      :thing="thing"
      @close="openInfoCard = false"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import DatastreamPopupPlot from '@/components/Datastream/DatastreamPopupPlot.vue'
import DatastreamForm from '@/components/Datastream/DatastreamForm.vue'
import DatastreamDeleteCard from './DatastreamDeleteCard.vue'
import Sparkline from '@/components/Sparkline.vue'
import {
  computed,
  nextTick,
  onBeforeUnmount,
  reactive,
  ref,
  toRef,
  watch,
} from 'vue'
import { useMetadata } from '@/composables/useMetadata'
import { storeToRefs } from 'pinia'
import { useThingStore } from '@/store/thing'
import { useWorkspaceStore } from '@/store/workspaces'
import { Datastream, Workspace, type StatusType } from '@hydroserver/client'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useTableLogic } from '@/composables/useTableLogic'
import { Snackbar } from '@/utils/notifications'
import { downloadDatastreamCsv } from '@/utils/csvExport'
import { formatTime } from '@/utils/time'
import { getTaskStatusText } from '@/utils/orchestration/taskRunDetails'
import DatastreamTableInfoCard from './DatastreamTableInfoCard.vue'
import ObservationsDeleteCard from '../Observation/ObservationsDeleteCard.vue'
import VisibilityTooltipCard from '@/components/Datastream/VisibilityTooltipCard.vue'
import hs, { PermissionAction, PermissionResource } from '@hydroserver/client'
import { useDisplay } from 'vuetify/lib/framework.mjs'
import {
  mdiAlertOctagon,
  mdiCallMerge,
  mdiChartBellCurve,
  mdiChartLine,
  mdiChevronRight,
  mdiContentCopy,
  mdiDelete,
  mdiDeleteOutline,
  mdiDotsVertical,
  mdiDownload,
  mdiFileEyeOutline,
  mdiFileRemove,
  mdiLightningBolt,
  mdiLinkOff,
  mdiLock,
  mdiLockOpenVariant,
  mdiMagnify,
  mdiPencil,
  mdiPlus,
  mdiSigma,
} from '@mdi/js'

const props = defineProps({
  workspace: { type: Object as () => Workspace, required: true },
  targetDatastreamId: { type: String, default: '' },
})

type LinkedDatastreamTask = {
  id: string
  name: string
  dataConnectionName: string | null
  displayName: string
  label: string
  icon: string
  iconClass: string
  status: StatusType
  paused: boolean
  lastRunAt: string | null
  route: {
    name: string
    params: { view: string }
    query: Record<string, string>
  }
}

const { thing } = storeToRefs(useThingStore())
const openCreate = ref(false)
const workspaceRef = toRef(props, 'workspace')
const thingIdRef = computed(() => thing.value!.id)
const downloading = reactive<Record<string, boolean>>({})
const search = ref()
const datastreamSectionRef = ref<any>(null)
const datastreamTableRef = ref<{
  scrollToIndex?: (index: number) => void
} | null>(null)
const highlightedDatastreamId = ref('')
const DATASTREAM_HIGHLIGHT_DURATION_MS = 2500
let highlightTimeout: number | undefined
const { smAndDown } = useDisplay()
const isMobile = computed(() => smAndDown.value)

const openObservationsDelete = ref(false)
function openObservationDialog(selectedItem: any) {
  item.value = selectedItem
  openObservationsDelete.value = true
}

const openInfoCard = ref(false)
const selectedDatastream = ref<Datastream | null>(null)
const openInfoCardFor = (datastream: Datastream) => {
  selectedDatastream.value = datastream
  openInfoCard.value = true
}

const { hasPermission } = useWorkspacePermissions(workspaceRef)
const { workspaces } = storeToRefs(useWorkspaceStore())

const canViewOrchestrationInfo = computed(() => {
  return workspaces.value.some(
    (workspace) => workspace.id === props.workspace.id
  )
})

const updateDatastream = async (updatedDatastream: Datastream) => {
  await fetchMetadata(props.workspace.id)
  onUpdate(updatedDatastream)
}

const onCreated = async () => {
  await fetchMetadata(props.workspace.id)
  await loadDatastreams()
}

const { item, items, openEdit, openDelete, openDialog, onUpdate, onDelete } =
  useTableLogic(
    async (thingId: string) =>
      await hs.datastreams.listAllItems({ thing_id: [thingId] }),
    hs.datastreams.delete,
    Datastream,
    thingIdRef
  )

const { sensors, units, observedProperties, processingLevels, fetchMetadata } =
  useMetadata(toRef(props, 'workspace'))

const openCharts = reactive<Record<string, boolean>>({})
const latestValues = reactive<
  Record<string, { text: string; showUnit: boolean; isBad: boolean }>
>({})
const linkedTasksByDatastreamId = ref<Record<string, LinkedDatastreamTask[]>>(
  {}
)
const linkedTasksLoaded = ref(false)
const linkedTasksErrored = ref(false)
let linkedTasksRequestId = 0

const handleLatestValueUpdate = (
  datastreamId: string,
  value: { text: string; showUnit: boolean; isBad: boolean }
) => {
  latestValues[datastreamId] = value
}

const latestValueFor = (datastreamId: string) =>
  latestValues[datastreamId] || { text: '—', showUnit: false, isBad: false }

const shouldShowLatestValue = (datastreamId: string) => {
  const value = latestValueFor(datastreamId)
  return value.text !== 'No observations'
}

const latestValueDisplay = (datastream: { id: string; unitName?: string }) => {
  const value = latestValueFor(datastream.id)
  if (!value.showUnit) return value.text
  return `${value.text} ${datastream.unitName ?? ''}`.trim()
}

const latestStatusClass = (datastream: Datastream) => {
  if (isDatastreamStale(datastream)) return 'text-[#9e9e9e]'
  const latestValue = latestValueFor(datastream.id)
  if (latestValue.isBad) return 'text-[#c86060]'
  return 'text-[#2e7d32]'
}

const visibleDatastreams = computed(() => {
  return items.value
    .filter(
      (d) =>
        !d.isPrivate ||
        hasPermission(
          PermissionResource.Datastream,
          PermissionAction.View,
          props.workspace
        )
    )
    .map((d) => {
      const unit = units.value.find((u) => u.id === d.unitId)
      const sensor = sensors.value.find((s) => s.id === d.sensorId)
      const op = observedProperties.value.find(
        (o) => o.id === d.observedPropertyId
      )
      const pl = processingLevels.value.find(
        (p) => p.id === d.processingLevelId
      )

      const mapped = {
        ...d,
        OPName: op ? `${op.name} (${op.code})` : '',
        processingLevelCode: pl?.code ?? '',
        processingLevelName: pl?.definition ?? '',
        sensorName: sensor?.name ?? '',
        unitName: unit?.name ?? '',
        searchText: ',',
        beginDate: formatTime(d.phenomenonBeginTime),
        endDate: formatTime(d.phenomenonEndTime),
        aggregationInterval: `${d.timeAggregationInterval} ${d.timeAggregationIntervalUnit}`,
        spacingInterval: `${d.intendedTimeSpacing} ${d.intendedTimeSpacingUnit}`,
      }

      mapped.searchText = [
        mapped.name,
        mapped.OPName,
        mapped.id,
        mapped.processingLevelName,
        mapped.sampledMedium,
        mapped.sensorName,
        mapped.noDataValue,
        mapped.aggregationStatistic,
        mapped.unitName,
        mapped.status,
        mapped.valueCount,
        mapped.beginDate,
        mapped.endDate,
        mapped.aggregationInterval,
        mapped.spacingInterval,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return mapped
    })
})

const normalizedSearch = computed(() =>
  (search.value ?? '').toString().trim().toLowerCase()
)

const tableDatastreams = computed(() => {
  const sorted = [...visibleDatastreams.value].sort((a, b) =>
    (a.name || a.OPName || '').localeCompare(b.name || b.OPName || '')
  )

  if (!normalizedSearch.value) return sorted
  return sorted.filter((item) =>
    (item.searchText || '').includes(normalizedSearch.value)
  )
})

const deepLinkedDatastreamId = computed(() => props.targetDatastreamId.trim())

const targetDatastreamIndex = computed(() => {
  if (!deepLinkedDatastreamId.value) return -1
  return tableDatastreams.value.findIndex(
    (datastream) => String(datastream.id) === deepLinkedDatastreamId.value
  )
})

function isTargetDatastream(datastreamId: string) {
  return (
    !!highlightedDatastreamId.value &&
    String(datastreamId) === highlightedDatastreamId.value
  )
}

function findTargetDatastreamElement() {
  if (!deepLinkedDatastreamId.value) return null
  const section = datastreamSectionElement()
  const elements = Array.from(
    section?.querySelectorAll<HTMLElement>('[data-datastream-id]') ?? []
  )
  return (
    elements.find(
      (element) => element.dataset.datastreamId === deepLinkedDatastreamId.value
    ) ?? null
  )
}

function datastreamSectionElement(): HTMLElement | null {
  const section = datastreamSectionRef.value
  if (!section) return null
  if (section instanceof HTMLElement) return section
  return section.$el instanceof HTMLElement ? section.$el : null
}

function highlightTargetDatastream() {
  highlightedDatastreamId.value = deepLinkedDatastreamId.value
  if (highlightTimeout) window.clearTimeout(highlightTimeout)
  highlightTimeout = window.setTimeout(() => {
    highlightedDatastreamId.value = ''
  }, DATASTREAM_HIGHLIGHT_DURATION_MS)
}

async function scrollToTargetDatastream() {
  if (!deepLinkedDatastreamId.value) return
  const canAccessDatastream = visibleDatastreams.value.some(
    (datastream) => String(datastream.id) === deepLinkedDatastreamId.value
  )
  if (!canAccessDatastream) return

  if (targetDatastreamIndex.value === -1 && normalizedSearch.value) {
    search.value = ''
    await nextTick()
  }

  await nextTick()
  datastreamSectionElement()?.scrollIntoView({
    block: 'start',
    behavior: 'smooth',
  })

  if (!isMobile.value && targetDatastreamIndex.value >= 0) {
    datastreamTableRef.value?.scrollToIndex?.(targetDatastreamIndex.value)
    await nextTick()
  }

  window.setTimeout(() => {
    findTargetDatastreamElement()?.scrollIntoView({
      block: 'center',
      behavior: 'smooth',
    })
    highlightTargetDatastream()
  }, 80)
}

const isDatastreamStale = (datastream: Datastream) => {
  if (!datastream.phenomenonEndTime) return true
  const endTime = new Date(datastream.phenomenonEndTime)
  const seventyTwoHoursAgo = new Date(Date.now() - 72 * 60 * 60 * 1000)
  return endTime < seventyTwoHoursAgo
}

const mobileDatastreams = computed(() => {
  return tableDatastreams.value
})

const linkedTasksForDatastream = (datastreamId: string) =>
  linkedTasksByDatastreamId.value[datastreamId] ?? []

const showTaskRow = computed(
  () => canViewOrchestrationInfo.value && linkedTasksLoaded.value
)

const showTaskSkeleton = computed(
  () =>
    canViewOrchestrationInfo.value &&
    !linkedTasksLoaded.value &&
    !linkedTasksErrored.value
)

const datastreamTaskLinkClass = (datastreamId: string) => {
  const linkedTasks = linkedTasksForDatastream(datastreamId)
  if (!linkedTasks.length) return 'datastream-task-link--none'
  if (linkedTasks.length > 1) return 'datastream-task-link--conflict'
  if (linkedTasks[0].paused) return 'datastream-task-link--none'

  const statusClass: Record<StatusType, string> = {
    OK: 'datastream-task-link--ok',
    Pending: 'datastream-task-link--pending',
    'Needs attention': 'datastream-task-link--attention',
    'Behind schedule': 'datastream-task-link--behind',
    Unknown: 'datastream-task-link--none',
    'Loading paused': 'datastream-task-link--none',
  }
  return statusClass[linkedTasks[0].status]
}

const TASK_STATUS_DOT_COLORS: Record<StatusType, string> = {
  OK: '#357a38',
  Pending: '#1769aa',
  'Needs attention': '#c62828',
  'Behind schedule': '#e65100',
  Unknown: '#546e7a',
  'Loading paused': '#546e7a',
}

const displayedTaskStatus = (task: LinkedDatastreamTask): StatusType =>
  task.paused && task.status !== 'Needs attention'
    ? 'Loading paused'
    : task.status

const taskStatusColor = (task: LinkedDatastreamTask) =>
  TASK_STATUS_DOT_COLORS[displayedTaskStatus(task)] ??
  TASK_STATUS_DOT_COLORS.Unknown

const formatRelativeTime = (iso: string | null) => {
  if (!iso) return null
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return null

  const diffSeconds = Math.round((Date.now() - then) / 1000)
  if (diffSeconds < 45) return 'just now'

  const units: [number, string][] = [
    [60, 'min'],
    [60, 'hr'],
    [24, 'day'],
    [30, 'mo'],
    [12, 'yr'],
  ]
  let value = diffSeconds / 60
  let label = 'min'
  for (let i = 1; i < units.length && value >= units[i][0]; i += 1) {
    value /= units[i][0]
    label = units[i][1]
  }
  const rounded = Math.round(value)
  return `${rounded} ${label}${rounded === 1 ? '' : 's'} ago`
}

const lastRanLabel = (task: LinkedDatastreamTask) => {
  const relative = formatRelativeTime(task.lastRunAt)
  return relative ? `Last ran ${relative}` : 'Never ran'
}

const routeForIngestionTask = (task: any) => {
  const query: Record<string, string> = {
    workspace_id: props.workspace.id,
    task_id: String(task.id),
  }
  const dataConnectionId = task.dataConnection?.id ?? task.dataConnectionId
  if (dataConnectionId) query.data_connection_id = String(dataConnectionId)

  return {
    name: 'OrchestrationIngestionDetails',
    params: { view: 'ingestion' },
    query,
  }
}

const dataProductRouteName = (task: any) => {
  if (task.aggregationTransformations?.length) {
    return 'OrchestrationAggregationDetails'
  }
  if (task.expressionTransformations?.length) {
    return 'OrchestrationExpressionDetails'
  }
  if (task.compositeExpressionTransformations?.length) {
    return 'OrchestrationDerivationDetails'
  }
  if (task.ratingCurveTransformations?.length) {
    return 'OrchestrationRatingCurveDetails'
  }
  return 'OrchestrationAggregationDetails'
}

const routeForDataProductTask = (task: any) => {
  const query: Record<string, string> = {
    workspace_id: props.workspace.id,
    task_id: String(task.id),
  }
  const siteId = task.thing?.id ?? task.thingId ?? thing.value?.id
  if (siteId) query.site_id = String(siteId)

  return {
    name: dataProductRouteName(task),
    params: { view: 'aggregation' },
    query,
  }
}

const outputDatastreamId = (transformation: any) =>
  transformation?.outputDatastream?.id ?? transformation?.outputDatastreamId

const targetDatastreamId = (mapping: any) =>
  mapping?.targetDatastream?.id ?? mapping?.targetDatastreamId

const taskPaused = (task: any) =>
  task.schedule ? task.schedule.enabled === false : false

const truncateTaskInfoPart = (value: unknown, maxLength = 250) => {
  const text = `${value ?? ''}`.trim()
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const dataConnectionNameForTask = (task: any) =>
  task.dataConnection?.name ?? task.dataConnectionName ?? null

const linkedTaskDisplayName = (task: any) => {
  const taskName = truncateTaskInfoPart(task.name || task.id)
  const dataConnectionName = dataConnectionNameForTask(task)
  if (!dataConnectionName) return taskName
  return `${truncateTaskInfoPart(dataConnectionName)} · ${taskName}`
}

const addLinkedTask = (
  grouped: Record<string, LinkedDatastreamTask[]>,
  seen: Set<string>,
  datastreamId: string,
  task: any,
  config: Pick<LinkedDatastreamTask, 'label' | 'icon' | 'route'> &
    Partial<Pick<LinkedDatastreamTask, 'iconClass'>>
) => {
  const key = `${datastreamId}:${task.id}`
  if (seen.has(key)) return
  seen.add(key)
  grouped[datastreamId] ??= []
  grouped[datastreamId].push({
    id: String(task.id),
    name: task.name,
    dataConnectionName: dataConnectionNameForTask(task),
    displayName: linkedTaskDisplayName(task),
    label: config.label,
    icon: config.icon,
    iconClass: config.iconClass ?? '',
    status: getTaskStatusText(task),
    paused: taskPaused(task),
    lastRunAt: task.latestRun?.startedAt ?? task.latestRun?.finishedAt ?? null,
    route: config.route,
  })
}

const loadLinkedTasks = async () => {
  const requestId = ++linkedTasksRequestId
  linkedTasksLoaded.value = false
  linkedTasksErrored.value = false
  const site = thing.value
  if (
    !canViewOrchestrationInfo.value ||
    !site ||
    !props.workspace?.id ||
    !items.value.length
  ) {
    linkedTasksByDatastreamId.value = {}
    return
  }

  const datastreamIds = new Set(items.value.map((d) => String(d.id)))
  try {
    const [etlTasks, dataProductTasks] = await Promise.all([
      hs.tasks.listAllItems({
        workspace_id: [props.workspace.id],
        order_by: ['name'],
        expand_related: true,
      } as any),
      hs.dataProductTasks.listAllItems({
        workspace_id: [props.workspace.id],
        thing_id: [site.id],
        order_by: ['name'],
        expand_related: true,
      } as any),
    ])
    if (requestId !== linkedTasksRequestId) return

    const grouped: Record<string, LinkedDatastreamTask[]> = {}
    const seen = new Set<string>()

    for (const task of etlTasks ?? []) {
      for (const mapping of (task as any).mappings ?? []) {
        const datastreamId = targetDatastreamId(mapping)
        if (!datastreamId || !datastreamIds.has(String(datastreamId))) continue
        addLinkedTask(grouped, seen, String(datastreamId), task, {
          label: 'Fed by',
          icon: mdiLightningBolt,
          iconClass: 'datastream-task-link__icon--source',
          route: routeForIngestionTask(task),
        })
      }
    }

    for (const task of dataProductTasks ?? []) {
      const transformationGroups = [
        {
          label: 'Aggregated by',
          icon: mdiCallMerge,
          iconClass: 'datastream-task-link__icon--aggregation',
          transformations: (task as any).aggregationTransformations ?? [],
        },
        {
          label: 'Derived by',
          icon: mdiSigma,
          iconClass: 'datastream-task-link__icon--derived',
          transformations: [
            ...((task as any).compositeExpressionTransformations ?? []),
            ...((task as any).expressionTransformations ?? []),
          ],
        },
        {
          label: 'Rating curve',
          icon: mdiChartBellCurve,
          iconClass: 'datastream-task-link__icon--rating-curve',
          transformations: (task as any).ratingCurveTransformations ?? [],
        },
      ]
      for (const group of transformationGroups) {
        for (const transformation of group.transformations) {
          const datastreamId = outputDatastreamId(transformation)
          if (!datastreamId || !datastreamIds.has(String(datastreamId)))
            continue
          addLinkedTask(grouped, seen, String(datastreamId), task, {
            label: group.label,
            icon: group.icon,
            iconClass: group.iconClass,
            route: routeForDataProductTask(task),
          })
        }
      }
    }

    linkedTasksByDatastreamId.value = grouped
    linkedTasksLoaded.value = true
  } catch (error) {
    if (requestId !== linkedTasksRequestId) return
    console.error('Error fetching linked datastream tasks', error)
    linkedTasksErrored.value = true
    linkedTasksByDatastreamId.value = {}
  }
}

watch(
  [
    () => props.workspace.id,
    canViewOrchestrationInfo,
    thingIdRef,
    () => items.value.map((d) => d.id).join(','),
  ],
  () => {
    void loadLinkedTasks()
  },
  { immediate: true }
)

watch(
  [
    deepLinkedDatastreamId,
    () => tableDatastreams.value.map((datastream) => datastream.id).join(','),
    isMobile,
  ],
  () => {
    void scrollToTargetDatastream()
  },
  { immediate: true, flush: 'post' }
)

onBeforeUnmount(() => {
  if (highlightTimeout) window.clearTimeout(highlightTimeout)
})

const onDownload = async (datastreamId: string) => {
  if (downloading[datastreamId]) return
  downloading[datastreamId] = true

  try {
    await downloadDatastreamCsv(datastreamId)
  } catch (err: any) {
    console.error('Error downloading datastream CSV', err)
    Snackbar.error(err.message)
  } finally {
    downloading[datastreamId] = false
  }
}

async function toggleDataVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  const previousIsVisible = datastream.isVisible
  const previousIsPrivate = datastream.isPrivate
  datastream.isVisible = !datastream.isVisible
  if (datastream.isVisible) datastream.isPrivate = false
  const didPersist = await patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
  if (!didPersist) {
    datastream.isVisible = previousIsVisible
    datastream.isPrivate = previousIsPrivate
  }
}

async function toggleVisibility(computedDatastream: Datastream) {
  // mutate the original
  const datastream = items.value.find((d) => d.id === computedDatastream.id)
  if (!datastream) return

  const previousIsVisible = datastream.isVisible
  const previousIsPrivate = datastream.isPrivate
  datastream.isPrivate = !datastream.isPrivate
  datastream.isVisible = !datastream.isPrivate
  const didPersist = await patchDatastream({
    id: datastream.id,
    isPrivate: datastream.isPrivate,
    isVisible: datastream.isVisible,
  })
  if (!didPersist) {
    datastream.isVisible = previousIsVisible
    datastream.isPrivate = previousIsPrivate
  }
}

const copyDatastreamId = async (id: string) => {
  try {
    await navigator.clipboard.writeText(id)
    Snackbar.success('Datastream ID copied to clipboard')
  } catch {
    Snackbar.error('Failed to copy datastream ID')
  }
}

const patchDatastream = async <T extends { id: string }>(patchBody: T) => {
  try {
    await hs.datastreams.update(patchBody)
    return true
  } catch (error) {
    console.error('Error updating datastream', error)
    return false
  }
}

async function onObservationsDelete() {
  try {
    await hs.datastreams.deleteObservations(item.value.id)
    items.value = []
    await loadDatastreams()
  } catch (error) {
    console.error('Failed to delete observations', error)
    Snackbar.error('Failed to delete observations')
  }
  openObservationsDelete.value = false
}

const loadDatastreams = async () => {
  try {
    items.value = await hs.datastreams.listAllItems({
      thing_id: [thing.value!.id],
    })
  } catch (e) {
    console.error('Error fetching datastreams', e)
  }
}
</script>

<style scoped>
/* Datastream list — plain card list (replaces the Vuetify data table for full
   layout control), modelled on the Claude Design "strip" prototype. */
.datastream-list {
  --datastream-list-grid: minmax(0, 1.1fr) minmax(0, 1.3fr) 10.75rem;
  --datastream-list-inline: calc(0.75rem + 1px + 0.85rem);
  padding: 0 0 0.75rem;
  background: #fafbfc;
  max-height: 100vh;
  overflow-y: auto;
}

.datastream-list__head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: var(--datastream-list-grid);
  gap: 1.25rem;
  padding: 0.5rem var(--datastream-list-inline);
  background: rgb(var(--v-theme-surface));
  border-bottom: 1px solid #e2e5e9;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.56);
}

.datastream-list__head-actions {
  text-align: right;
}

.ds-card {
  margin: 0.5rem 0.75rem 0;
  background: #fff;
  border: 1px solid #e2e5e9;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.ds-card--highlighted {
  border-color: #1565c0;
  box-shadow: 0 0 0 2px rgba(21, 101, 192, 0.18);
}

.ds-card__grid {
  display: grid;
  grid-template-columns: var(--datastream-list-grid);
  gap: 1.25rem;
  padding: 0.6rem 0.85rem;
}

.ds-card__grid > .datastream-actions {
  align-items: flex-end;
}

.datastream-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 1rem;
  background: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-on-secondary));
  border-radius: 12px 12px 0 0;
}

.datastream-toolbar__left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1 1 420px;
  min-width: 220px;
}

.datastream-toolbar__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-left: auto;
}

.datastream-toolbar__title {
  margin: 0;
  line-height: 1.2;
  color: inherit;
}

.datastream-toolbar :deep(.v-field__input) {
  color: rgb(var(--v-theme-on-secondary));
}

.datastream-toolbar :deep(.v-field__prepend-inner) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-label) {
  color: rgba(var(--v-theme-on-secondary), 0.8);
}

.datastream-toolbar :deep(.v-field__outline__start),
.datastream-toolbar :deep(.v-field__outline__end) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__outline__notch) {
  border-color: rgba(var(--v-theme-on-secondary), 0.5);
}

.datastream-toolbar :deep(.v-field__clearable) {
  color: rgba(var(--v-theme-on-secondary), 0.9);
}

.datastream-search {
  max-width: 260px;
  min-width: 200px;
  flex: 0 1 260px;
}

@media (max-width: 1200px) {
  .datastream-toolbar__left {
    flex-direction: column;
    align-items: flex-start;
  }

  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

.datastream-latest {
  display: flex;
  flex-direction: column;
  padding-top: 0;
}

.datastream-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.6rem;
}

.datastream-card {
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.datastream-card--highlighted {
  border-color: #1565c0;
  box-shadow: 0 0 0 2px rgba(21, 101, 192, 0.18);
}

.datastream-card__content {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.datastream-card__title {
  font-weight: 600;
  font-size: 1rem;
}

.datastream-card__icons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.datastream-card__actions {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.datastream-card__meta-btn {
  align-self: flex-start;
}

.datastream-title {
  font-weight: 600;
  font-size: 1rem;
  max-width: 360px;
  overflow-wrap: anywhere;
}

.datastream-info-list,
.datastream-time-list {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-top: 0;
}

.datastream-line {
  margin: 0;
  line-height: 1.3;
}

.datastream-id {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.datastream-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.datastream-actions__icons {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 32px;
  flex-wrap: wrap;
}

.datastream-download {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.datastream-task-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  margin-top: 0.75rem;
  padding: 0.55rem 0.65rem;
  border-left: 3px solid #546e7a;
  border-radius: 6px;
  background: #eceff1;
  color: rgba(0, 0, 0, 0.87);
}

/* Task strip sits flush at the bottom of each card as an integral footer. */
.datastream-task-link--card {
  margin-top: 0;
  border-radius: 0;
  width: 100%;
  padding: 0.45rem 0.85rem;
  border-top: 1px solid #eef0f3;
}

.datastream-task-link--ok {
  border-left-color: #357a38;
  background: #e8f5e9;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--attention,
.datastream-task-link--conflict {
  border-left-color: #c62828;
  background: #fdecea;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--pending {
  border-left-color: #1769aa;
  background: #e3f1fd;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--behind {
  border-left-color: #e65100;
  background: #fff3e0;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--none {
  border-left-color: #546e7a;
  background: #eceff1;
  color: rgba(0, 0, 0, 0.87);
}

.datastream-task-link--loading {
  border-left-color: #90a4ae;
  background: #f3f6f8;
  color: rgba(0, 0, 0, 0.38);
}

.datastream-task-link__loading-icon,
.datastream-task-link__loading-bar {
  display: block;
  flex: none;
  border-radius: 999px;
  background:
    linear-gradient(
      90deg,
      rgba(120, 144, 156, 0.14) 0%,
      rgba(120, 144, 156, 0.28) 42%,
      rgba(120, 144, 156, 0.14) 82%
    );
  background-size: 220% 100%;
  animation: datastream-task-skeleton 1.4s ease-in-out infinite;
}

.datastream-task-link__loading-icon {
  width: 1.1rem;
  height: 1.1rem;
}

.datastream-task-link__loading-bar {
  height: 0.48rem;
}

.datastream-task-link__loading-bar--label {
  width: 8rem;
  max-width: 38%;
}

.datastream-task-link__loading-bar--name {
  width: 20rem;
  max-width: 68%;
}

.datastream-task-link__icon--source {
  color: #2196f3 !important;
}

.datastream-task-link__icon--derived {
  color: #6a1b9a !important;
}

.datastream-task-link__icon--aggregation {
  color: #6a1b9a !important;
}

.datastream-task-link__icon--rating-curve {
  color: #283593 !important;
}

.datastream-task-link__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.datastream-task-link__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.45rem 0.85rem;
}

.datastream-task-link__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.42);
}

.datastream-task-link__name {
  color: rgba(0, 0, 0, 0.87);
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: none;
}

.datastream-task-link__name:hover,
.datastream-task-link__tasks a:hover {
  text-decoration: underline;
}

.datastream-task-link__status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.datastream-task-link__dot {
  display: inline-block;
  width: 0.44rem;
  height: 0.44rem;
  border-radius: 50%;
  flex: none;
}

.datastream-task-link__last-ran {
  font-size: 0.7rem;
  font-weight: 500;
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.42);
}

.datastream-task-link__conflict-text {
  font-weight: 700;
}

.datastream-task-link__tasks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.75rem;
}

.datastream-task-link__tasks a {
  color: inherit;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 2px;
}

@keyframes datastream-task-skeleton {
  0% {
    background-position: 120% 0;
  }

  100% {
    background-position: -120% 0;
  }
}

@media (max-width: 960px) {
  .datastream-search {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

@media (max-width: 700px) {
  .datastream-toolbar__left,
  .datastream-toolbar__actions {
    width: 100%;
  }

  .datastream-toolbar__left {
    flex-direction: column;
    align-items: stretch;
  }

  .datastream-toolbar__actions {
    justify-content: flex-start;
  }

  .datastream-toolbar__actions :deep(.v-btn) {
    width: 100%;
    justify-content: center;
  }

  .datastream-info-list,
  .datastream-time-list {
    gap: 0.35rem;
  }

  .datastream-copy-btn {
    min-width: 40px;
    min-height: 40px;
  }
}

@media (min-width: 961px) {
  .datastream-info-list,
  .datastream-time-list {
    gap: 0.2rem;
  }
}
</style>
