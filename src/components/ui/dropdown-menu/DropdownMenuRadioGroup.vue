<script setup lang="ts">
// 下拉菜单单选组
import type { DropdownMenuRadioGroupEmits, DropdownMenuRadioGroupProps } from "reka-ui"
import {
  DropdownMenuRadioGroup,
  useForwardPropsEmits,
} from "reka-ui"

const props = defineProps<DropdownMenuRadioGroupProps>()
const emits = defineEmits<DropdownMenuRadioGroupEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <DropdownMenuRadioGroup
    data-slot="dropdown-menu-radio-group"
    v-bind="forwarded"
  >
    <slot />
  </DropdownMenuRadioGroup>
</template>
