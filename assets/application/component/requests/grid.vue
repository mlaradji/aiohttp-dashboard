<template>
    <div class="container-fluid">
        <div class="row mt-3 mb-3">
            <div class="col-md-12">
                <b-card class="shadow" title="Requests">
                    <b-table @row-clicked="(item, index) => details(item.id, index)" 
                             :responsive="true"
                             :hover="true"
                             :items="requests"
                             :fields="fields"
                             striped
                             class="table-pointer">

                    <template slot="status" slot-scope="row">
                        <span class="badge" :class="getStatusClassByCode(row.value)">
                            {{row.value}}
                        </span>
                    </template>

                    </b-table>
                </b-card>
            </div>
        </div>

        <bar v-if="requests" sticky="bottom" align="center" :card="false">            
            <b-pagination :limit="3" :per-page="50" v-model="page" align="center"/>
        </bar>
    </div>
</template>


<script type="text/javascript">
    import _ from "lodash"
    import {WebSocketService} from '@/websocket'
    import {router} from '@/router'


    export default {
        mixins: [WebSocketService.mixin],
        data: () => ({
            fields: {
                status: {label: 'Status'},
                path: {label: 'Path'},
                method: {label: 'Method'},
                begintime: {label: 'Begin time'},
                donetime: {label: 'End time'},
            },

            requests: [],
            page: 1,
        }),
        methods: {
            details: function(id) {
                router.push({path: `/request/detail/${id}`})
            },

            getStatusClassByCode(code) {
                if (_.startsWith(code, 4)) {
                    return 'badge-warning'
                } else if (_.startsWith(code, 5)) {
                    return 'badge-danger'
                } else {
                    return 'badge-success'
                }
            }
        },
        created: function() {
            this.subscription = this.subscribe('requests', message => {
                this.requests = message.data
            });
        },
        destroyed: function() {
            this.unsibscribe(this.subscription);
        }
    }
</script>

