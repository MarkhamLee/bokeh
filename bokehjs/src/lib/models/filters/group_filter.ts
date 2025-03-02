import {Filter} from "./filter"
import type * as p from "core/properties"
import {Indices} from "core/types"
import {logger} from "core/logging"
import type {ColumnarDataSource} from "../sources/columnar_data_source"

export namespace GroupFilter {
  export type Attrs = p.AttrsOf<Props>

  export type Props = Filter.Props & {
    column_name: p.Property<string>
    group: p.Property<string>
  }
}

export interface GroupFilter extends GroupFilter.Attrs {}

export class GroupFilter extends Filter {
  declare properties: GroupFilter.Props

  constructor(attrs?: Partial<GroupFilter.Attrs>) {
    super(attrs)
  }

  static {
    this.define<GroupFilter.Props>(({String}) => ({
      column_name: [ String ],
      group:       [ String ],
    }))
  }

  compute_indices(source: ColumnarDataSource): Indices {
    const column = source.get_column(this.column_name)
    const size = source.get_length() ?? 1
    if (column == null) {
      logger.warn(`${this}: groupby column '${this.column_name}' not found in the data source`)
      return Indices.all_set(size)
    } else {
      const indices = new Indices(size, 0)
      for (let i = 0; i < indices.size; i++) {
        if (column[i] === this.group)
          indices.set(i)
      }
      return indices
    }
  }
}
